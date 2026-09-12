"""Ticket intake: a just-received ticket's raw restriction notes become exactly one event.

17: "Normalization output is cached on the ticket, not recomputed" — so normalization is
recorded in the log as TICKET_RESTRICTION_RESOLVED or TICKET_BLOCKED (12 §Ticket events)
immediately after TICKET_RECEIVED, by the replay runner and the runtime alike. A re-run of
the normalizer can then never silently alter an in-flight ticket's meaning.
"""

from __future__ import annotations

from src.domain import EvidenceGrade, Knowledge, Resolution
from src.events import DraftEvent, DraftTicketBlocked, DraftTicketRestrictionResolved

from .normalizer import DEFAULT_THRESHOLD, _restriction, _score


def intake(
    ticket_id: str,
    restrictions_raw: list[str],
    k: Knowledge,
    *,
    t: int,
    station_id: str,
    event_id_prefix: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[DraftEvent]:
    """Return exactly one draft event for the ticket's restriction notes.

    Every note RESOLVED (or no notes at all) -> ``DraftTicketRestrictionResolved`` carrying
    the normalized restrictions. Any AMBIGUOUS or UNRESOLVABLE note -> ``DraftTicketBlocked``
    whose reason is ``"<RESOLUTION>: <raw>"`` per offending note, ``"; "``-joined. Both are
    ``source="ORDER_SYSTEM"``, ``grade=ASSERTED``; ``confidence`` is metadata only (ADR-0004)
    and records the lowest normalizer score on the ticket.
    """
    scored = [(raw, _score(raw, k)) for raw in restrictions_raw]
    restrictions = [_restriction(raw, score, threshold) for raw, score in scored]
    confidence = min((score.confidence for _, score in scored), default=1.0)
    blocked = [r for r in restrictions if r.resolution is not Resolution.RESOLVED]
    events: list[DraftEvent]
    if blocked:
        events = [
            DraftTicketBlocked(
                ticket=ticket_id,
                reason="; ".join(f"{r.resolution.value}: {r.raw_text}" for r in blocked),
                event_id=f"{event_id_prefix}:blocked",
                t_occurred=t,
                station_id=station_id,
                source="ORDER_SYSTEM",
                grade=EvidenceGrade.ASSERTED,
                confidence=confidence,
            )
        ]
    else:
        events = [
            DraftTicketRestrictionResolved(
                ticket=ticket_id,
                restrictions=restrictions,
                event_id=f"{event_id_prefix}:resolved",
                t_occurred=t,
                station_id=station_id,
                source="ORDER_SYSTEM",
                grade=EvidenceGrade.ASSERTED,
                confidence=confidence,
            )
        ]
    return events
