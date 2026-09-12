"""L1: scenario loading, event expansion, initial-state seeding and config overrides. Needs no
reasoning core: the seeded WorldState is built by hand from the station config."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain import (
    CarrierKind,
    EpistemicStatus,
    EvidenceGrade,
    Mode,
    Resolution,
    Station,
    StationConfig,
    Strength,
    WorldState,
)
from src.replay import (
    ScenarioFile,
    apply_overrides,
    build_event,
    load_scenario,
    seed_state,
    sorted_events,
)

from .conftest import core_for

_CONFIG = {"station": "demo", "knowledge": "demo", "profile": "eval"}


def _scenario(events: list[dict], **extra) -> ScenarioFile:  # type: ignore[type-arg]
    return ScenarioFile(
        scenario="unit", description="unit", config=_CONFIG, events=events, expect=[], **extra
    )


def _bare_state(station: StationConfig) -> WorldState:
    return WorldState(
        station=Station(
            station_id=station.station_id,
            config_version=station.config_version,
            knowledge_version=station.knowledge_version,
            mode=Mode.REPLAY,
            carriers=station.carriers,
            zones=station.zones,
            worker_slots=station.worker_slots,
        ),
        zone_allergens=station.zone_allergens,
    )


# ---- ScenarioFile ----------------------------------------------------------------------------


def test_scenario_file_requires_t_and_type_on_every_event() -> None:
    with pytest.raises(ValidationError, match="`t` must be an integer"):
        _scenario([{"type": "TICKET_BOUND", "ticket": "T1"}])
    with pytest.raises(ValidationError, match="`type` must be"):
        _scenario([{"t": 0}])
    with pytest.raises(ValidationError):
        _scenario([{"t": True, "type": "TICKET_BOUND"}])


def test_load_scenario_reads_yaml(tmp_path: Path) -> None:
    path = tmp_path / "x.yaml"
    path.write_text(
        "scenario: x\ndescription: d\nschema_version: 1\nhazard: true\n"
        "config: { station: demo, knowledge: demo, profile: eval }\n"
        "events:\n  - { t: 0, type: TICKET_BOUND, ticket: T1 }\nexpect:\n  - { silence: true }\n"
    )
    sf = load_scenario(path)
    assert sf.scenario == "x" and sf.hazard and sf.events[0]["ticket"] == "T1"
    (tmp_path / "bad.yaml").write_text("- not\n- a\n- mapping\n")
    with pytest.raises(ValueError, match="top level"):
        load_scenario(tmp_path / "bad.yaml")


# ---- sorting and expansion -------------------------------------------------------------------


def test_sorted_events_orders_by_time_then_file_order() -> None:
    sf = _scenario(
        [
            {"t": 5, "type": "A", "n": 0},
            {"t": 1, "type": "B", "n": 1},
            {"t": 5, "type": "C", "n": 2},
        ]
    )
    assert [index for index, _ in sorted_events(sf)] == [1, 0, 2]


def test_build_event_fills_envelope_and_payload_defaults() -> None:
    contact = build_event(
        {"t": 10, "type": "CONTACT_BEGIN", "a": "gloves", "b": "board"},
        scenario="s",
        seq=3,
        station_id="st",
    )
    assert contact.event_id == "s:0003" and contact.seq == 3
    assert contact.t_occurred == contact.t_committed == 10
    assert contact.source == "PERCEPTION" and contact.grade == EvidenceGrade.OBSERVED
    assert contact.contact_point.x == 0 and contact.contact_point.y == 0

    bound = build_event(
        {"t": 0, "type": "TICKET_BOUND", "ticket": "T1"}, scenario="s", seq=0, station_id="st"
    )
    assert bound.source == "OPERATOR" and bound.worker_slot == 0

    asserted = build_event(
        {"t": 0, "type": "OPERATOR_ASSERTION", "carrier": "board", "claim": "REPLACED"},
        scenario="s",
        seq=0,
        station_id="st",
    )
    assert asserted.grade == EvidenceGrade.ASSERTED and asserted.source == "OPERATOR"

    received = build_event(
        {
            "t": 0,
            "type": "TICKET_RECEIVED",
            "ticket": "T1",
            "items": ["turkey_sandwich"],
            "restrictions": [{"raw_text": "pine nut allergy"}],
        },
        scenario="s",
        seq=0,
        station_id="st",
    )
    assert received.source == "ORDER_SYSTEM" and received.order_source == "fixture"
    assert received.restrictions[0].raw_text == "pine nut allergy"
    assert received.restrictions[0].resolution == Resolution.AMBIGUOUS

    mode = build_event(
        {"t": 0, "type": "STATION_MODE_CHANGED", "mode": "PROTOCOL_ONLY", "cause": "x"},
        scenario="s",
        seq=0,
        station_id="st",
    )
    assert mode.source == "SYSTEM"


def test_build_event_honours_explicit_source_and_grade() -> None:
    event = build_event(
        {"t": 0, "type": "GLOVE_CHANGE", "phase": "DON", "grade": "INFERRED", "source": "OPERATOR"},
        scenario="s",
        seq=0,
        station_id="st",
    )
    assert event.grade == EvidenceGrade.INFERRED and event.source == "OPERATOR"


def test_build_event_rejects_malformed_events() -> None:
    with pytest.raises(ValidationError):
        build_event({"t": 0, "type": "NOT_A_TYPE"}, scenario="s", seq=0, station_id="st")
    with pytest.raises(ValidationError):  # missing `zone`
        build_event(
            {"t": 0, "type": "ZONE_ENTRY", "carrier": "gloves"},
            scenario="s",
            seq=0,
            station_id="st",
        )
    with pytest.raises(ValidationError):  # catalog: human resets must be ASSERTED
        build_event(
            {
                "t": 0,
                "type": "OPERATOR_ASSERTION",
                "carrier": "b",
                "claim": "CLEAN",
                "grade": "OBSERVED",
            },
            scenario="s",
            seq=0,
            station_id="st",
        )


# ---- seeding -----------------------------------------------------------------------------


def test_seed_state_applies_taints_epistemic_and_provenance() -> None:
    _, station, _ = core_for("eval", "demo", "demo")
    state = _bare_state(station)
    seeded = seed_state(
        state,
        {
            "carriers": {
                "gloves": {
                    "taints": {"PINE_NUT": {"grade": "OBSERVED", "hops": 0}},
                    "epistemic": "TRACKED",
                },
                "board": {"taints": {"PINE_NUT": {"hops": 1, "strength": "POSSIBLE"}}},
                "landing": {"epistemic": "STALE"},
            }
        },
    )
    gloves = seeded.station.carriers["gloves"]
    record = gloves.taints["PINE_NUT"]
    assert record.grade == EvidenceGrade.OBSERVED and record.hops == 0
    assert record.acquired_at == 0 and record.source_carrier_id == "seed"
    assert record.source_event_id == "seed:gloves:PINE_NUT"
    assert gloves.epistemic == EpistemicStatus.TRACKED and gloves.last_observed_at == 0

    board = seeded.station.carriers["board"]
    assert board.taints["PINE_NUT"].hops == 1
    assert board.taints["PINE_NUT"].strength == Strength.POSSIBLE
    assert board.taints["PINE_NUT"].grade == EvidenceGrade.OBSERVED  # default
    assert board.epistemic == state.station.carriers["board"].epistemic  # untouched

    landing = seeded.station.carriers["landing"]
    assert landing.epistemic == EpistemicStatus.STALE and not landing.taints

    assert seeded.acquisitions["gloves"] == [record]
    assert seeded.station.recent_allergen_exposure == {"PINE_NUT": 0}
    assert state.station.carriers["gloves"].taints == {}  # input untouched


def test_seed_state_rejects_unknown_carriers_and_keys() -> None:
    _, station, _ = core_for("eval", "demo", "demo")
    state = _bare_state(station)
    with pytest.raises(ValueError, match="not a station carrier"):
        seed_state(state, {"carriers": {"spatula": {"epistemic": "TRACKED"}}})
    with pytest.raises(ValueError, match="unknown keys"):
        seed_state(state, {"tickets": {}})
    with pytest.raises(ValueError, match="unknown keys"):
        seed_state(state, {"carriers": {"gloves": {"taint": {}}}})
    assert seed_state(state, {}) == state


# ---- overrides ---------------------------------------------------------------------------


def test_apply_overrides_maps_dotted_keys_onto_config() -> None:
    cfg, _, _ = core_for("eval", "demo", "demo")
    out = apply_overrides(
        cfg,
        {
            "contamination.max_hops": 5,
            "contamination.station_recent_window_s": 60,
            "temporal.t_stale_s.GLOVES": 7,
            "temporal.t_escalate_s": 3,
            "temporal.t_dwell_ms": 123,
        },
    )
    assert out.max_hops == 5
    assert out.station_recent_window == 60_000
    assert out.t_stale[CarrierKind.GLOVES] == 7_000
    assert out.t_stale[CarrierKind.TOOL] == cfg.t_stale[CarrierKind.TOOL]
    assert out.t_escalate == 3_000
    assert out.t_dwell == 123
    assert cfg.max_hops != 5, "input config is never mutated"
    assert apply_overrides(cfg, {}) == cfg


def test_apply_overrides_rejects_unknown_keys_and_bad_values() -> None:
    cfg, _, _ = core_for("eval", "demo", "demo")
    with pytest.raises(ValueError, match="unknown config override"):
        apply_overrides(cfg, {"contamination.max_hop": 3})
    with pytest.raises(ValueError):
        apply_overrides(cfg, {"contamination.max_hops": "three"})
    with pytest.raises(ValueError):
        apply_overrides(cfg, {"temporal.t_stale_s.SPATULA": 3})
