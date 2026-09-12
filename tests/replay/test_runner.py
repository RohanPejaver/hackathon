"""L2: runner mechanics that no A-M fixture exercises directly — quarantine of a malformed
event (23 P10), the intake draft that follows TICKET_RECEIVED, override errors, and JSON
serialisability of the result."""

from __future__ import annotations

import json

import pytest

from src.replay import ScenarioFile

from .conftest import runner_of

_CONFIG = {"station": "demo", "knowledge": "demo", "profile": "eval"}


def _scenario(events: list[dict], expect: list[dict] | None = None, **extra) -> ScenarioFile:  # type: ignore[type-arg]
    return ScenarioFile(
        scenario="unit-runner",
        description="unit",
        config={**_CONFIG, **extra.pop("config", {})},
        events=events,
        expect=expect or [],
        **extra,
    )


def test_malformed_event_is_quarantined_not_crashed_on() -> None:
    sf = _scenario(
        [
            {"t": 0, "type": "NOT_A_TYPE"},
            {"t": 100, "type": "ZONE_ENTRY", "carrier": "gloves"},  # missing `zone`
            {"t": 200, "type": "ZONE_ENTRY", "carrier": "gloves", "zone": "bin:pesto"},
        ],
        expect=[
            {"event_rejected": {"index": 0}},
            {"event_rejected": {"event_id_suffix": ":0001"}},
            {
                "at": 200,
                "state_at": {"carriers": {"gloves": {"taints": {"PINE_NUT": {"hops": 0}}}}},
            },
        ],
    )
    result = runner_of(sf).run(sf)
    assert [r.index for r in result.rejected] == [0, 1]
    assert result.rejected[0].event_id == "unit-runner:0000"
    health = [e for e in result.derived_events if e.type == "HEALTH_DEGRADED"]
    assert [h.rejected_event_id for h in health] == ["unit-runner:0000", "unit-runner:0001"]
    assert [e.seq for e in result.events] == list(range(len(result.events))), "seq stays gapless"
    assert result.passed, [a.detail for a in result.assertions if not a.passed]


def test_ticket_received_is_followed_by_the_intake_draft() -> None:
    sf = _scenario(
        [
            {
                "t": 0,
                "type": "TICKET_RECEIVED",
                "ticket": "T1",
                "items": ["turkey_sandwich"],
                "restrictions": [{"raw_text": "pine nut allergy"}],
            },
            {
                "t": 0,
                "type": "TICKET_RECEIVED",
                "ticket": "T2",
                "items": ["turkey_sandwich"],
                "restrictions": [{"raw_text": "ALLERGY"}],
            },
            {"t": 0, "type": "TICKET_RECEIVED", "ticket": "T3", "items": ["turkey_sandwich"]},
        ]
    )
    result = runner_of(sf).run(sf)
    kinds = [(e.seq, e.type, e.t_occurred) for e in result.events]
    assert kinds == [
        (0, "TICKET_RECEIVED", 0),
        (1, "TICKET_RESTRICTION_RESOLVED", 0),
        (2, "TICKET_RECEIVED", 0),
        (3, "TICKET_BLOCKED", 0),
        (4, "TICKET_RECEIVED", 0),
        (5, "TICKET_RESTRICTION_RESOLVED", 0),
    ]
    resolved = result.events[1]
    assert resolved.restrictions[0].allergen_ids == frozenset({"PINE_NUT"})
    assert resolved.event_id.startswith("unit-runner:0000")
    tickets = result.final_state.tickets
    assert tickets["T1"].lifecycle.value == "RECEIVED"
    assert tickets["T2"].lifecycle.value == "BLOCKED"
    assert tickets["T3"].lifecycle.value == "RECEIVED"


def test_unknown_override_is_an_error() -> None:
    sf = _scenario([], config={"overrides": {"contamination.max_hop": 1}})
    with pytest.raises(ValueError, match="unknown config override"):
        runner_of(sf).run(sf)


def test_result_round_trips_through_json() -> None:
    sf = _scenario(
        [{"t": 0, "type": "ZONE_ENTRY", "carrier": "gloves", "zone": "bin:pesto"}],
        expect=[{"silence": True}],
    )
    result = runner_of(sf).run(sf)
    payload = json.loads(result.model_dump_json())
    assert payload["scenario"] == "unit-runner" and payload["passed"] is True
    assert payload["mode_timeline"][0]["mode"] == "REPLAY"
    assert [s["event_id"] for s in payload["states"]] == ["seed", "unit-runner:0000"]
