"""Composition root (30 rule 4; 39 §1; ADR-0012). One process, one asyncio loop:
    drain queue -> reorder -> append log -> reduce -> risk -> policy -> broadcast -> serve UI
    -> accept worker actions.
This is the only module allowed to import broadly, read a clock and do I/O. Perception is
never imported at module scope (39 §2: the core runs with opencv absent).

Run: `uvicorn src.runtime.app:app` — profile/station/knowledge from STATION_PROFILE,
STATION_ID, KNOWLEDGE_ID (defaults demo/demo/demo). With no perception pipeline configured the
station runs in PROTOCOL_ONLY (ADR-0011). STATION_REPLAY=<scenario.yaml|session.jsonl> runs
the same loop from a log reader in REPLAY mode (10 §Runtime modes).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from collections import deque
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from src import domain as dom
from src import events as ev
from src.knowledge import KnowledgeProvider
from src.orders import ManualEntrySource, intake
from src.policy import AlertState, evaluate
from src.replay import seed_state
from src.risk import assess
from src.runtime.clock import Clock, LogClock, SystemClock
from src.runtime.config import LoadedConfig, load, to_domain
from src.runtime.controller import RuntimeController
from src.runtime.feed import FeedItem, jsonl_feed, scenario_feed
from src.state import initial, reduce
from src.ui import wire
from src.ui.server import create_app as create_fastapi

LIVE = (
    dom.TicketLifecycle.BOUND,
    dom.TicketLifecycle.IN_PREP,
    dom.TicketLifecycle.COMPLETE,
    dom.TicketLifecycle.HELD,
)
TICK_S = 0.1
DERIVED = {
    "ALERT_RAISED",
    "ALERT_UPDATED",
    "ALERT_RESOLVED",
    "ALERT_ESCALATED",
    "ALERT_SUPPRESSED",
    "TICKET_HELD",
}
ALERT_TYPE = {
    "RAISE": "ALERT_RAISED",
    "UPDATE": "ALERT_UPDATED",
    "RESOLVE": "ALERT_RESOLVED",
    "ESCALATE": "ALERT_ESCALATED",
    "SUPPRESS": "ALERT_SUPPRESSED",
}


def _participants(e: Any) -> list[str]:
    out: list[str] = []
    for f in ("a", "b", "carrier", "zone", "retired", "introduced", "ticket", "alert_id"):
        v = getattr(e, f, None)
        if isinstance(v, str):
            out.append(v)
    return out


def _summary(e: Any) -> str:
    t = e.type
    if t in ("CONTACT_BEGIN", "CONTACT_END"):
        return f"{e.a} <-> {e.b}"
    if t in ("ZONE_ENTRY", "ZONE_EXIT"):
        return f"{e.carrier} -> {e.zone}"
    if t in ("TOOL_SWAP", "SURFACE_SWAP"):
        return f"{e.retired} -> {e.introduced} from {e.from_zone}"
    if t == "SURFACE_WIPE":
        return f"{e.carrier} wiped — not a reset"
    if t == "OPERATOR_ASSERTION":
        return f"{e.carrier} {e.claim.lower()} (asserted)"
    if t == "GLOVE_CHANGE":
        return f"slot {e.worker_slot} {e.phase.lower()}"
    if t == "STATION_MODE_CHANGED":
        return f"-> {e.mode} ({e.cause})"
    if t == "CARRIER_OBSERVABILITY_CHANGED":
        return f"{e.carrier} -> {e.epistemic} ({e.cause})"
    if t == "TRACK_IDENTITY_SUSPECT":
        return f"{e.a} ? {e.b} — taints merged, both STALE"
    if t == "HEALTH_DEGRADED":
        return str(e.cause)
    if t.startswith("TICKET_"):
        return f"#{e.ticket} {t[7:].lower().replace('_', ' ')}"
    if t.startswith("ALERT_"):
        return f"{e.alert_id} {t[6:].lower()}"
    if t == "CONFIG_LOADED":
        return f"config v{e.config_version} knowledge v{e.knowledge_version}"
    return str(t)


class Runtime:
    def __init__(self, loaded: LoadedConfig, clock: Clock, log_dir: Path | None) -> None:
        self.loaded = loaded
        self.cfg, self.station_cfg, self.k = to_domain(loaded)
        self.kp = KnowledgeProvider(self.k)
        self.clock = clock
        self.log = ev.EventLog(self.cfg.t_reorder)
        self.sink = ev.EventSink(self.log, self.clock.now)
        self.controller = RuntimeController(
            self._emit_dict, self.clock, loaded.values.temporal.t_recover_s
        )
        self.state: dom.WorldState = initial(self.cfg, self.station_cfg)
        self.alerts = AlertState(self.cfg)
        self.manual = ManualEntrySource()
        self.recent: deque[wire.EventLine] = deque(maxlen=200)
        self.last_contact: dict[str, int] = {}
        self.rejected: list[str] = []
        self.feed: list[FeedItem] = []  # REPLAY inputs, time-ordered; empty when live
        self._feed_origin = 0
        self._wall_start: int | None = None
        self._n = 0
        self._jsonl = None
        if log_dir is not None:
            log_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            self._jsonl = (log_dir / f"{stamp}.jsonl").open("a")
        self.log.subscribe(self._on_committed)
        self.controller.report_config(True)
        self.emit(
            "CONFIG_LOADED",
            source="SYSTEM",
            config_version=self.cfg.config_version,
            knowledge_version=self.cfg.knowledge_version,
        )

    # ---- event construction ------------------------------------------------------------------
    def _event_id(self) -> str:
        self._n += 1
        return f"rt-{self._n:06d}"

    def emit(self, type_: str, *, source: str, grade: str | None = None, **fields: Any) -> str:
        """Build a draft of `type_` and hand it to the sink; never raises into the caller."""
        eid = self._event_id()
        if grade is None:
            grade = "ASSERTED" if type_ in ("WASH_CYCLE", "OPERATOR_ASSERTION") else "OBSERVED"
        draft = ev.DRAFTEVENT_ADAPTER.validate_python(
            {
                "type": type_,
                "event_id": eid,
                "t_occurred": self.clock.now(),
                "station_id": self.station_cfg.station_id,
                "source": source,
                "grade": grade,
                **fields,
            }
        )
        self.sink.emit(draft)
        return eid

    def _emit_dict(self, d: dict[str, Any]) -> None:
        payload = dict(d.get("payload", {}))
        payload.pop("previous", None)
        self.emit(d["type"], source=d["source"], grade=d.get("grade"), **payload)

    # ---- the loop: one committed event at a time ----------------------------------------------
    def _on_committed(self, e: Any) -> None:
        ge = ev.project(e)
        if e.type == "CONTACT_BEGIN" or e.type == "ZONE_ENTRY":
            for p in _participants(e):
                self.last_contact[p] = e.t_occurred
        try:
            if self.controller.health()["reasoning"] == "OK":
                self.state, _ = reduce(self.state, ge, self.cfg)
                self.alerts.observe(ge)
                if ge.mutates_state:
                    self._assess(e.t_occurred, e.event_id)
        except Exception as exc:  # 23 P11: never fail open; holds persist; incident logged
            self.controller.report_core_exception(e.event_id, exc)
        self.controller.report_committed(e.late)
        self.recent.append(
            wire.EventLine(
                seq=e.seq,
                event_id=e.event_id,
                t_occurred=e.t_occurred,
                type=e.type,
                source=e.source,
                grade=e.grade,
                participants=_participants(e),
                mutates_state=e.mutates_state,
                late=e.late,
                summary=_summary(e),
            )
        )
        if self._jsonl is not None:
            self._jsonl.write(e.model_dump_json() + "\n")
            self._jsonl.flush()

    def _assess(self, t: int, cause: str) -> None:
        live = sorted(
            (tk for tk in self.state.tickets.values() if tk.lifecycle in LIVE),
            key=lambda tk: tk.ticket_id,
        )
        assessments = assess(self.state, live, self.k, self.cfg)
        for cmd in evaluate(assessments, self.alerts, self.cfg, state=self.state):
            alert = self.alerts.apply(cmd)
            self.emit(
                ALERT_TYPE[cmd.kind],
                source="SYSTEM",
                alert_id=alert.alert_id,
                pathway_signature=alert.pathway_signature,
                command=cmd.model_dump(mode="json"),
            )
            ticket = self.state.tickets.get(alert.ticket_id)
            if (
                cmd.kind in ("RAISE", "ESCALATE")
                and int(alert.tier) == 2
                and ticket is not None
                and ticket.lifecycle != dom.TicketLifecycle.HELD
            ):
                self.emit(
                    "TICKET_HELD", source="SYSTEM", ticket=alert.ticket_id, alert_id=alert.alert_id
                )

    # ---- periodic work ---------------------------------------------------------------------------
    def load_replay(self, source: str | Path) -> None:
        """REPLAY: a scenario fixture (.yaml) or a recorded session log (.jsonl)."""
        path = Path(source)
        if path.suffix in (".yaml", ".yml"):
            scenario, self.feed, taint_seed = scenario_feed(path, self.station_cfg.station_id)
            if taint_seed["carriers"]:
                self.state = seed_state(self.state, taint_seed)
        else:
            self.feed = jsonl_feed(path)
        self._feed_origin = self.feed[0].t if self.feed else 0
        if isinstance(self.clock, LogClock):
            self.clock.advance_to(self._feed_origin)

    def feed_until(self, t: int) -> int:
        """Emit every replay input due at or before t (log time); returns how many."""
        n = 0
        while self.feed and self.feed[0].t <= t:
            item = self.feed.pop(0)
            if isinstance(self.clock, LogClock):
                self.clock.advance_to(item.t)
            self.sink.emit(item.draft)
            if item.needs_intake and isinstance(item.draft, ev.DraftTicketReceived):
                received = item.draft
                for draft in intake(
                    received.ticket,
                    [r.raw_text for r in received.restrictions],
                    self.k,
                    t=item.t,
                    station_id=self.station_cfg.station_id,
                    event_id_prefix=received.event_id,
                ):
                    self.sink.emit(draft)
            n += 1
        if isinstance(self.clock, LogClock):
            self.clock.advance_to(t)
        return n

    def tick(self) -> None:
        if self.feed or self._wall_start is not None:
            # Real-time playback: log time advances with the wall clock from the first input.
            wall = SystemClock().now()
            if self._wall_start is None:
                self._wall_start = wall
            self.feed_until(self._feed_origin + (wall - self._wall_start))
        now = self.clock.now()
        for raw in self.manual.poll():
            self.emit(
                "TICKET_RECEIVED",
                source="ORDER_SYSTEM",
                ticket=raw.external_id,
                items=raw.items,
                restrictions=[
                    dom.Restriction(raw_text=n).model_dump(mode="json") for n in raw.notes
                ],
                order_source="manual",
            )
            for draft in intake(
                raw.external_id,
                raw.notes,
                self.k,
                t=now,
                station_id=self.station_cfg.station_id,
                event_id_prefix=self._event_id(),
                threshold=self.cfg.normalizer_threshold,
            ):
                self.sink.emit(draft)
            self.manual.ack(raw.external_id)
        self.log._drain(now)  # the reorder pump; commit time is injected (19, Q2)

    # ---- worker actions: events only, never state (22 WorkerDisplay) ----------------------------
    def on_action(self, body: dict[str, Any]) -> dict[str, Any]:
        kind = body.get("kind")
        slot = int(body.get("worker_slot", 0))
        try:
            if kind == "NEW_TICKET":
                notes = [r["raw_text"] for r in body.get("restrictions", []) if r.get("raw_text")]
                self.manual.submit(
                    str(body["ticket_id"]), list(body["items"]), notes, self.clock.now()
                )
                return {"accepted": True}
            if kind == "BIND_TICKET":
                tk = self.state.tickets.get(body["ticket_id"])
                if tk is None:
                    return {"accepted": False, "reason": "unknown ticket"}
                if not self.controller.bind_allowed():
                    return {"accepted": False, "reason": f"no binding in {self.controller.mode()}"}
                if tk.lifecycle != dom.TicketLifecycle.RECEIVED or any(
                    r.resolution != dom.Resolution.RESOLVED for r in tk.restrictions
                ):
                    return {
                        "accepted": False,
                        "reason": f"ticket is {tk.lifecycle}; restriction unresolved",
                    }
                eid = self.emit(
                    "TICKET_BOUND", source="OPERATOR", ticket=tk.ticket_id, worker_slot=slot
                )
                return {"accepted": True, "event_id": eid}
            if kind == "PREP_STARTED":
                return {
                    "accepted": True,
                    "event_id": self.emit(
                        "TICKET_PREP_STARTED", source="OPERATOR", ticket=body["ticket_id"]
                    ),
                }
            if kind == "ITEM_COMPLETE":
                return {
                    "accepted": True,
                    "event_id": self.emit(
                        "TICKET_ITEM_COMPLETE", source="OPERATOR", ticket=body["ticket_id"]
                    ),
                }
            if kind == "RESOLVE_HOLD":
                return {
                    "accepted": True,
                    "event_id": self.emit(
                        "TICKET_RELEASED",
                        source="OPERATOR",
                        ticket=body["ticket_id"],
                        worker_slot=slot,
                    ),
                }
            if kind == "REMAKE":
                tk = self.state.tickets[body["ticket_id"]]
                self.emit("TICKET_VOIDED", source="OPERATOR", ticket=tk.ticket_id, reason="remake")
                eid = self.emit(
                    "TICKET_REWORK_OPENED",
                    source="OPERATOR",
                    ticket=f"{tk.ticket_id}R",
                    rework_of=tk.ticket_id,
                    items=list(tk.items),
                    restrictions=[r.model_dump(mode="json") for r in tk.restrictions],
                )
                return {"accepted": True, "event_id": eid}
            if kind in ("ASSERT_CLEAN", "ASSERT_REPLACED"):
                claim = "CLEAN" if kind == "ASSERT_CLEAN" else "REPLACED"
                ids = [
                    self.emit(
                        "OPERATOR_ASSERTION",
                        source="OPERATOR",
                        carrier=c,
                        claim=claim,
                        worker_slot=slot,
                    )
                    for c in body["carrier_ids"]
                ]
                return {"accepted": True, "event_ids": ids}
            if kind in ("ACKNOWLEDGE", "DISMISS"):
                alert = next(
                    (a for a in self.alerts.open() if a.alert_id == body["alert_id"]), None
                )
                if alert is None:
                    return {"accepted": False, "reason": "no such open alert"}
                if kind == "DISMISS" and int(alert.tier) == 2:
                    return {"accepted": False, "reason": "a hold cannot be dismissed (26)"}
                eid = self.emit(
                    "ALERT_ACKNOWLEDGED" if kind == "ACKNOWLEDGE" else "ALERT_UPDATED",
                    source="OPERATOR",
                    alert_id=alert.alert_id,
                    pathway_signature=alert.pathway_signature,
                    worker_slot=slot,
                )
                return {"accepted": True, "event_id": eid}
            if kind == "REQUEST_MODE":  # dev/run-book only; not on the worker display
                self.controller.request_mode(body["mode"], str(body.get("cause", "operator")))
                return {"accepted": True, "mode": self.controller.mode()}
            return {"accepted": False, "reason": f"unknown action {kind!r}"}
        except (KeyError, TypeError, ValueError) as exc:
            return {"accepted": False, "reason": f"{type(exc).__name__}: {exc}"}

    # ---- the projection both routes read (25: the inspector has no privileged view) -------------
    def snapshot(self) -> dict[str, Any]:
        now = self.clock.now()
        st = self.state.station
        carriers = [
            c.model_copy(update={"epistemic": dom.effective_epistemic(c, now, self.cfg)})
            for c in st.carriers.values()
        ]
        summary = dom.StationSummary(
            station_id=st.station_id,
            mode=st.mode,
            config_version=st.config_version,
            knowledge_version=st.knowledge_version,
            carriers=carriers,
            tickets=list(self.state.tickets.values()),
            conditions=list(self.state.conditions),
            t_occurred=self.state.t_occurred,
        )
        h = self.controller.health()
        zones = [
            wire.ZoneInfo(
                zone_id=z.zone_id,
                kind=z.kind,
                contents=list(z.contents),
                bound_carrier=z.bound_carrier,
                allergens=sorted(self.state.zone_allergens.get(z.zone_id, {})),
                polygon=[(p.x, p.y) for p in z.polygon],
                last_contact_at=self.last_contact.get(z.zone_id)
                or (self.last_contact.get(z.bound_carrier) if z.bound_carrier else None),
            )
            for z in st.zones.values()
        ]
        menu_names = {
            m.item_id: m.display_name for m in self.loaded.knowledge.menu_items.menu_items
        }
        snap = wire.Snapshot(
            schema_version=1,
            state_summary=summary,
            interventions=self.alerts.open(),
            runtime=wire.RuntimeInfo(
                time=wire.TimeRef(t=now, kind=self.clock.kind),
                seq=self.recent[-1].seq if self.recent else 0,
                health=wire.Health(**h),
                recent_events=list(self.recent),
                zones=zones,
                menu=[wire.MenuItem(item_id=k, display_name=v) for k, v in menu_names.items()],
                config_checksum=self.loaded.config_checksum,
                knowledge_checksum=self.loaded.knowledge.checksum,
                rejected=list(self.log._quarantine),
            ),
        )
        return snap.model_dump(mode="json")


def build(
    profile: str = "demo",
    station_id: str = "demo",
    knowledge_id: str = "demo",
    config_root: str = "config",
    log_dir: Path | None = Path("data/logs"),
    replay: str | Path | None = None,
) -> Runtime:
    loaded = load(config_root, profile, station_id, knowledge_id)  # type: ignore[arg-type]
    clock: Clock = LogClock(0) if replay else SystemClock()
    rt = Runtime(loaded, clock, log_dir)
    rt.controller.report_vision("UNAVAILABLE")  # no perception pipeline in this build
    if replay:
        rt.load_replay(replay)
        rt.controller.request_mode("REPLAY", f"replaying {Path(replay).name}")
    else:
        rt.controller.request_mode("PROTOCOL_ONLY", "no perception pipeline configured")
    return rt


def make_app() -> FastAPI:
    replay_src = os.environ.get("STATION_REPLAY")
    rt = build(
        profile=os.environ.get("STATION_PROFILE", "demo"),
        station_id=os.environ.get("STATION_ID", "demo"),
        knowledge_id=os.environ.get("KNOWLEDGE_ID", "demo"),
        replay=replay_src,
    )
    push_hz = rt.loaded.values.runtime.ui_push_hz

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async def loop() -> None:
            while True:
                rt.tick()
                await asyncio.sleep(TICK_S)

        task = asyncio.create_task(loop())
        try:
            yield
        finally:
            task.cancel()

    app = create_fastapi(rt.snapshot, rt.on_action, push_hz)
    app.router.lifespan_context = lifespan
    app.state.runtime = rt
    return app


app = (
    make_app()
    if os.environ.get("STATION_NO_AUTOSTART") is None and __name__ != "__main__"
    else None
)


def _selftest() -> None:  # pragma: no cover
    rt = build(log_dir=None)
    print(json.dumps(rt.snapshot())[:300])


if __name__ == "__main__":
    _selftest()
