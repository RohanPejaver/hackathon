"""Deterministic replay runner (22 §ReplayRunner, 36).

The fold is the runtime's fold: for every committed event in seq order, project it, reduce,
let the alert state observe it, and — when it can change risk — assess the live tickets
and apply the policy's commands. The runner receives already-built `Config`,
`StationConfig` and `Knowledge` (it never loads config itself; `runtime/` is the only
composition root, 30 rule 4) and reads no clock: time is `t_occurred`.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue, ValidationError

from src.domain import (
    AlertCommand,
    Config,
    Knowledge,
    Mode,
    StationConfig,
    Ticket,
    TicketLifecycle,
    WorldState,
)
from src.events import EVENT_ADAPTER, Event, GradedEvent, TicketReceived, project
from src.orders import intake
from src.policy import AlertState, evaluate
from src.risk import assess
from src.state import initial, reduce

from .assertions import evaluate_assertions
from .loader import apply_overrides, build_event, event_id_for, seed_state, sorted_events
from .schema import (
    ModeChange,
    Rejection,
    ReplayResult,
    ScenarioFile,
    StateSnapshot,
    TimedCommand,
    TimedPathway,
)

_LIVE = frozenset(
    {
        TicketLifecycle.BOUND,
        TicketLifecycle.IN_PREP,
        TicketLifecycle.COMPLETE,
        TicketLifecycle.HELD,
    }
)
_ALERT_EVENT = {
    "RAISE": "ALERT_RAISED",
    "UPDATE": "ALERT_UPDATED",
    "RESOLVE": "ALERT_RESOLVED",
    "ESCALATE": "ALERT_ESCALATED",
    "SUPPRESS": "ALERT_SUPPRESSED",
}


class ReplayRunner:
    def __init__(self, cfg: Config, station: StationConfig, k: Knowledge) -> None:
        self._cfg = cfg
        self._station = station
        self._k = k

    def run(self, scenario: ScenarioFile) -> ReplayResult:
        cfg = apply_overrides(self._cfg, scenario.config.overrides)
        station = self._station.model_copy(update={"mode": Mode.REPLAY})
        state = seed_state(initial(cfg, station), scenario.initial_state)
        fold = _Fold(scenario.scenario, cfg, self._k, state)
        for index, raw in sorted_events(scenario):
            fold.commit_fixture_event(index, raw)
        return fold.finish(scenario.expect)


class _Fold:
    """Mutable accumulators for one run; everything it records is ordered by seq."""

    def __init__(self, scenario: str, cfg: Config, k: Knowledge, state: WorldState) -> None:
        self.scenario = scenario
        self.cfg = cfg
        self.k = k
        self.state = state
        self.alerts = AlertState(cfg)
        self.seq = 0
        self.events: list[Event] = []
        self.derived: list[Event] = []
        self.commands: list[TimedCommand] = []
        self.pathways: list[TimedPathway] = []
        self.rejected: list[Rejection] = []
        self.mode_timeline = [ModeChange(t=0, mode=state.station.mode)]
        self.states = [StateSnapshot(t=0, event_id="seed", state=state)]

    # -- commit paths -------------------------------------------------------------------------

    def commit_fixture_event(self, index: int, raw: Mapping[str, JsonValue]) -> None:
        station_id = self.state.station.station_id
        try:
            event = build_event(raw, scenario=self.scenario, seq=self.seq, station_id=station_id)
        except (ValidationError, ValueError, TypeError) as exc:
            self._quarantine(index, raw, str(exc))
            return
        self._commit(event)
        if isinstance(event, TicketReceived):
            drafts = intake(
                event.ticket,
                [r.raw_text for r in event.restrictions],
                self.k,
                t=event.t_occurred,
                station_id=station_id,
                event_id_prefix=event.event_id,
            )
            for draft in drafts:
                self._commit(self._committed(draft.model_dump(), t=event.t_occurred))

    def _quarantine(self, index: int, raw: Mapping[str, JsonValue], reason: str) -> None:
        """23 P10 / EventLog.append semantics: a malformed event is recorded as HEALTH_DEGRADED
        with the reason, and the fold continues."""
        rejected_id = event_id_for(self.scenario, self.seq)
        self.rejected.append(Rejection(index=index, event_id=rejected_id, reason=reason))
        t = raw.get("t")
        health = self._committed(
            {
                "type": "HEALTH_DEGRADED",
                "event_id": f"{self.scenario}:health:{self.seq:04d}",
                "source": "SYSTEM",
                "grade": "ASSERTED",
                "cause": f"rejected fixture event {index}: {reason}",
                "rejected_event_id": rejected_id,
            },
            t=t if isinstance(t, int) and not isinstance(t, bool) else 0,
        )
        self.derived.append(health)
        self._commit(health)

    def _committed(self, payload: Mapping[str, object], *, t: int) -> Event:
        data: dict[str, object] = {
            **payload,
            "seq": self.seq,
            "t_committed": t,
            "station_id": self.state.station.station_id,
        }
        data.setdefault("event_id", event_id_for(self.scenario, self.seq))
        data.setdefault("t_occurred", t)
        return EVENT_ADAPTER.validate_python(data)

    def _commit(self, event: Event) -> None:
        self.seq += 1
        self.events.append(event)
        graded = project(event)
        self._fold(graded)
        if graded.mutates_state:
            self._assess(event.event_id, event.t_occurred)
        self.states.append(
            StateSnapshot(t=event.t_occurred, event_id=event.event_id, state=self.state)
        )

    def _fold(self, graded: GradedEvent) -> None:
        self.state, _ = reduce(self.state, graded, self.cfg)
        self.alerts.observe(graded)
        mode = self.state.station.mode
        if mode != self.mode_timeline[-1].mode:
            self.mode_timeline.append(ModeChange(t=graded.t_occurred, mode=mode))

    # -- risk and policy -----------------------------------------------------------------------

    def _assess(self, cause_event_id: str, t: int) -> None:
        live: list[Ticket] = sorted(
            (tk for tk in self.state.tickets.values() if tk.lifecycle in _LIVE),
            key=lambda tk: tk.ticket_id,
        )
        assessments = assess(self.state, live, self.k, self.cfg)
        for assessment in assessments:
            for pathway in assessment.pathways:
                self.pathways.append(
                    TimedPathway(t=t, ticket_id=assessment.ticket_id, pathway=pathway)
                )
        for cmd in evaluate(assessments, self.alerts, self.cfg):
            alert = self.alerts.apply(cmd)
            self.commands.append(TimedCommand(t=t, command=cmd))
            self._emit_alert_event(cmd)
            ticket = self.state.tickets.get(alert.ticket_id)
            if (
                cmd.kind in ("RAISE", "ESCALATE")
                and int(alert.tier) == 2
                and ticket is not None
                and ticket.lifecycle != TicketLifecycle.HELD
            ):
                held = self._committed(
                    {
                        "type": "TICKET_HELD",
                        "source": "SYSTEM",
                        "grade": "OBSERVED",
                        "ticket": alert.ticket_id,
                        "alert_id": alert.alert_id,
                    },
                    t=cmd.t_occurred,
                )
                self.seq += 1
                self.events.append(held)
                self.derived.append(held)
                self._fold(project(held))

    def _emit_alert_event(self, cmd: AlertCommand) -> None:
        event = self._committed(
            {
                "type": _ALERT_EVENT[cmd.kind],
                "source": "SYSTEM",
                "grade": "OBSERVED",
                "alert_id": cmd.alert.alert_id,
                "pathway_signature": cmd.alert.pathway_signature,
                "command": cmd,
            },
            t=cmd.t_occurred,
        )
        self.seq += 1
        self.events.append(event)
        self.derived.append(event)

    # -- result ---------------------------------------------------------------------------------

    def finish(self, expect: list[dict[str, JsonValue]]) -> ReplayResult:
        alerts = sorted(self.alerts.all(), key=lambda a: a.alert_id)
        result = ReplayResult(
            scenario=self.scenario,
            final_state=self.state,
            alerts=alerts,
            traces=[step for alert in alerts for step in alert.derivation],
            commands=self.commands,
            events=self.events,
            derived_events=self.derived,
            mode_timeline=self.mode_timeline,
            rejected=self.rejected,
            pathways=self.pathways,
            states=self.states,
        )
        assertions = evaluate_assertions(expect, result)
        return result.model_copy(
            update={"assertions": assertions, "passed": all(a.passed for a in assertions)}
        )
