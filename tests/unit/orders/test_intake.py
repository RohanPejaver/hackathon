"""Ticket intake -> exactly one TICKET_RESTRICTION_RESOLVED or TICKET_BLOCKED draft."""

from __future__ import annotations

import pytest

from src.domain import EvidenceGrade, Knowledge, Resolution
from src.events import DRAFTEVENT_ADAPTER, DraftTicketBlocked, DraftTicketRestrictionResolved
from src.orders import intake, normalize

ENVELOPE = {"t": 1_000, "station_id": "demo-bagel", "event_id_prefix": "T48"}


def test_no_restrictions_resolves_with_empty_list(k: Knowledge) -> None:
    events = intake("T48", [], k, **ENVELOPE)
    assert len(events) == 1
    e = events[0]
    assert isinstance(e, DraftTicketRestrictionResolved)
    assert e.type == "TICKET_RESTRICTION_RESOLVED"
    assert e.ticket == "T48"
    assert e.restrictions == []
    assert e.event_id == "T48:resolved"
    assert e.t_occurred == 1_000
    assert e.station_id == "demo-bagel"
    assert e.source == "ORDER_SYSTEM"
    assert e.grade is EvidenceGrade.ASSERTED


def test_resolved_event_carries_the_normalized_restrictions(k: Knowledge) -> None:
    raw = ["pine nut allergy", "no pesto"]
    (e,) = intake("T48", raw, k, **ENVELOPE)
    assert isinstance(e, DraftTicketRestrictionResolved)
    assert e.restrictions == [normalize(r, k) for r in raw]
    assert all(r.resolution is Resolution.RESOLVED for r in e.restrictions)
    assert e.restrictions[0].allergen_ids == frozenset({"PINE_NUT"})
    assert e.confidence == 1.0


def test_ambiguous_blocks_with_reason(k: Knowledge) -> None:
    (e,) = intake("T49", ["ALLERGY"], k, **ENVELOPE)
    assert isinstance(e, DraftTicketBlocked)
    assert e.type == "TICKET_BLOCKED"
    assert e.ticket == "T49"
    assert e.reason == "AMBIGUOUS: ALLERGY"
    assert e.reason.startswith("AMBIGUOUS:")
    assert e.event_id == "T48:blocked"
    assert e.source == "ORDER_SYSTEM"
    assert e.grade is EvidenceGrade.ASSERTED


def test_unresolvable_blocks_with_reason(k: Knowledge) -> None:
    (e,) = intake("T50", ["no durian"], k, **ENVELOPE)
    assert isinstance(e, DraftTicketBlocked)
    assert e.reason == "UNRESOLVABLE: no durian"


def test_one_bad_note_blocks_the_whole_ticket(k: Knowledge) -> None:
    (e,) = intake("T51", ["pine nut allergy", "ALLERGY", "no durian"], k, **ENVELOPE)
    assert isinstance(e, DraftTicketBlocked)
    assert e.reason == "AMBIGUOUS: ALLERGY; UNRESOLVABLE: no durian"


@pytest.mark.parametrize(
    "raw", [[], ["pine nut allergy"], ["ALLERGY"], ["no durian"], ["vegan", "no nuts"]]
)
def test_exactly_one_event_always(k: Knowledge, raw: list[str]) -> None:
    assert len(intake("T1", raw, k, **ENVELOPE)) == 1


@pytest.mark.parametrize("raw", [[], ["pine nut allergy", "no pesto"], ["ALLERGY"], ["no durian"]])
def test_drafts_validate_against_the_catalog(k: Knowledge, raw: list[str]) -> None:
    for d in intake("T1", raw, k, **ENVELOPE):
        again = DRAFTEVENT_ADAPTER.validate_python(d.model_dump())
        assert again == d
        assert DRAFTEVENT_ADAPTER.validate_json(d.model_dump_json()) == d


def test_threshold_is_passed_through(k: Knowledge) -> None:
    (blocked,) = intake("T2", ["pinenut allergy"], k, **ENVELOPE)
    assert isinstance(blocked, DraftTicketBlocked)
    assert blocked.reason == "AMBIGUOUS: pinenut allergy"
    assert blocked.confidence == 0.6
    (ok,) = intake("T2", ["pinenut allergy"], k, threshold=0.5, **ENVELOPE)
    assert isinstance(ok, DraftTicketRestrictionResolved)
    assert ok.restrictions[0].allergen_ids == frozenset({"PINE_NUT"})
    assert ok.confidence == 0.6


def test_intake_is_pure(k: Knowledge) -> None:
    a = intake("T3", ["no nuts", "ALLERGY"], k, **ENVELOPE)
    b = intake("T3", ["no nuts", "ALLERGY"], k, **ENVELOPE)
    assert a == b
