"""In-memory append-only committed log with a private draft reorder buffer (Q2)."""
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from pydantic import ValidationError

from src.domain import EvidenceGrade, WorldState

from .catalog import DRAFTEVENT_ADAPTER, EVENT_ADAPTER, DraftEvent, DraftHealthDegraded, Event


class SchemaError(ValueError):
    """A rejected event was quarantined and health degradation recorded."""


class ClockError(ValueError):
    """Commit time would precede the preceding commit."""


@dataclass(frozen=True)
class Subscription:
    handler: Callable[[Event], None]


class EventLog:
    def __init__(self, t_reorder: int) -> None:
        if t_reorder < 0:
            raise ValueError("t_reorder must be nonnegative")
        self._window = t_reorder
        self._events: list[Event] = []
        self._handlers: list[Subscription] = []
        self._pending: list[tuple[int, DraftEvent]] = []
        self._quarantine: list[str] = []
        self._max_occurred = -1

    def append(self, e: Event) -> int:
        try:
            accepted = EVENT_ADAPTER.validate_python(e.model_dump())
            if accepted.seq != len(self._events):
                raise ValueError("seq must be gapless")
            if any(old.event_id == accepted.event_id for old in self._events):
                raise ValueError("event_id must be unique")
        except (ValidationError, ValueError) as exc:
            self._reject(str(exc), e.station_id, e.t_occurred, e.t_committed, e.event_id)
            raise SchemaError(str(exc)) from exc
        if self._events and accepted.t_committed < self._events[-1].t_committed:
            self._reject("commit clock regressed", e.station_id, e.t_occurred, self._events[-1].t_committed, e.event_id)
            raise ClockError("commit clock regressed")
        self._events.append(accepted.model_copy(deep=True))
        self._max_occurred = max(self._max_occurred, accepted.t_occurred)
        for subscription in tuple(self._handlers):
            subscription.handler(accepted.model_copy(deep=True))
        return accepted.seq

    def read(self, from_seq: int, to: int | None = None) -> Iterator[Event]:
        # CONTRACT-GAP: 22 'from' is a Python keyword; half-open sequence range.
        return (e.model_copy(deep=True) for e in self._events[from_seq:to])

    def subscribe(self, handler: Callable[[Event], None]) -> Subscription:
        subscription = Subscription(handler)
        self._handlers.append(subscription)
        return subscription

    def snapshot_at(self, seq: int) -> WorldState | None:
        # 13 explicitly defers snapshots; 22 permits absence. No cache is built.
        return None

    def _ingest(self, draft: DraftEvent, committed_at: int) -> None:
        checked = DRAFTEVENT_ADAPTER.validate_python(draft.model_dump())
        self._pending.append((committed_at, checked.model_copy(deep=True)))
        self._drain(committed_at)

    def _drain(self, now: int, *, force: bool = False) -> None:
        # CONTRACT-GAP: private pump, injected commit time; runtime calls at its queue tick.
        # Buffer by arrival time, sort all available drafts before committing an eligible prefix.
        self._pending.sort(key=lambda pair: (pair[1].t_occurred, pair[1].event_id))
        while self._pending:
            arrival, draft = self._pending[0]
            if not force and now - arrival < self._window:
                break
            self._pending.pop(0)
            event = EVENT_ADAPTER.validate_python({
                **draft.model_dump(), "seq": len(self._events), "t_committed": now,
                "late": draft.t_occurred < self._max_occurred,
            })
            self.append(event)

    def _reject(self, reason: str, station: str, occurred: int, committed: int, event_id: str) -> None:
        self._quarantine.append(reason)
        draft = DraftHealthDegraded(
            event_id=f"health:{len(self._events)}:{len(self._quarantine)}",
            station_id=station, t_occurred=occurred, source="SYSTEM",
            grade=EvidenceGrade.ASSERTED, cause=reason, rejected_event_id=event_id,
        )
        health = EVENT_ADAPTER.validate_python({
            **draft.model_dump(), "seq": len(self._events), "t_committed": committed,
            "late": occurred < self._max_occurred,
        })
        self._events.append(health)
        for subscription in tuple(self._handlers):
            try:
                subscription.handler(health.model_copy(deep=True))
            except Exception as exc:
                self._quarantine.append(f"health subscriber: {exc}")


class EventSink:
    def __init__(self, log: EventLog, clock: Callable[[], int]) -> None:
        self._log = log
        self._clock = clock

    def emit(self, e: DraftEvent) -> None:
        try:
            self._log._ingest(e, self._clock())
        except Exception as exc:
            # P10: no malformed draft or downstream callback escapes into UI/perception.
            try:
                self._log._reject(str(exc), getattr(e, "station_id", "unknown"),
                                  getattr(e, "t_occurred", 0), self._clock(),
                                  getattr(e, "event_id", "malformed"))
            except Exception as failure:
                self._log._quarantine.append(str(failure))
