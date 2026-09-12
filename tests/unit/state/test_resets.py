"""14 §Reset semantics: the only taint-clearing events, and the one that must not clear."""

from __future__ import annotations

from src.domain import (
    CarrierKind,
    Config,
    EpistemicStatus,
    EvidenceGrade,
    ResetKind,
    WorldState,
)
from src.state import reduce
from tests.unit.state.conftest import contact, ev, fold, glove_don, zone_entry


def dirty(state: WorldState, cfg: Config) -> WorldState:
    """gloves, spreader and board all carry PINE_NUT."""
    return fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "spreader"),
            contact(300, "spreader", "board"),
        ],
        cfg,
    )


# -- SURFACE_WIPE: the counter-intuitive one (ADR-0009, scenario J) -----------------------


def test_surface_wipe_is_identity(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    new, deltas = reduce(s, ev("SURFACE_WIPE", 400, carrier="board"), cfg)
    assert new is s
    assert deltas == []
    assert "PINE_NUT" in new.station.carriers["board"].taints
    assert new.t_occurred == 300 and new.event_ids == s.event_ids


# -- GLOVE_CHANGE -------------------------------------------------------------------------


def test_glove_don_clears_gloves_and_records_reset(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    e = glove_don(400, grade="INFERRED")
    new, deltas = reduce(s, e, cfg)
    gloves = new.station.carriers["gloves"]
    assert gloves.taints == {}
    assert gloves.epistemic == EpistemicStatus.TRACKED
    assert gloves.last_observed_at == 400
    assert gloves.clean_grade is None
    assert new.resets[-1].model_dump() == {
        "event_id": e.event_id,
        "t_occurred": 400,
        "carrier_id": "gloves",
        "grade": EvidenceGrade.INFERRED,
        "operator": False,
    }
    assert "PINE_NUT" in new.station.carriers["spreader"].taints  # only gloves reset
    assert new.acquisitions["gloves"]  # history survives the reset
    assert {d.rule_id for d in deltas} == {"glove_change_reset"}
    assert any(d.field == "taints" and d.after == {} for d in deltas)


def test_glove_doff_is_observation_only(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    new, deltas = reduce(s, ev("GLOVE_CHANGE", 400, worker_slot=0, phase="DOFF"), cfg)
    assert "PINE_NUT" in new.station.carriers["gloves"].taints
    assert new.station.carriers["gloves"].last_observed_at == 400
    assert new.resets == []
    assert {d.rule_id for d in deltas} <= {"observation"}


def test_glove_change_prefers_slot_matched_gloves(state: WorldState, cfg: Config) -> None:
    from src.domain import Carrier

    st = state.station
    carriers = dict(st.carriers)
    carriers["gloves"] = carriers["gloves"].model_copy(update={"worker_slot": 0})
    carriers["gloves_b"] = Carrier(carrier_id="gloves_b", kind=CarrierKind.GLOVES, worker_slot=1)
    s = state.model_copy(update={"station": st.model_copy(update={"carriers": carriers})})
    s = fold(s, [zone_entry(1, "gloves", "bin:pesto"), zone_entry(2, "gloves_b", "bin:pesto")], cfg)
    new = fold(s, [glove_don(10, slot=1)], cfg)
    assert new.station.carriers["gloves_b"].taints == {}
    assert "PINE_NUT" in new.station.carriers["gloves"].taints
    new = fold(s, [glove_don(10, slot=7)], cfg)  # no match: every GLOVES carrier resets
    assert new.station.carriers["gloves"].taints == {}
    assert new.station.carriers["gloves_b"].taints == {}


def test_glove_change_without_gloves_carrier_is_rejected(state: WorldState, cfg: Config) -> None:
    st = state.station
    carriers = {k: v for k, v in st.carriers.items() if v.kind != CarrierKind.GLOVES}
    s = state.model_copy(update={"station": st.model_copy(update={"carriers": carriers})})
    new, deltas = reduce(s, glove_don(10), cfg)
    assert new is s and deltas == []


# -- TOOL_SWAP / SURFACE_SWAP -------------------------------------------------------------


def test_tool_swap_retires_and_introduces(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    e = ev("TOOL_SWAP", 400, retired="spreader", introduced="spreader_2", from_zone="clean_stock")
    new, deltas = reduce(s, e, cfg)
    assert "spreader" not in new.station.carriers
    fresh = new.station.carriers["spreader_2"]
    assert fresh.kind == CarrierKind.TOOL
    assert fresh.taints == {}
    assert fresh.epistemic == EpistemicStatus.TRACKED
    assert fresh.last_observed_at == 400
    assert fresh.home_zone == "tool_rack"
    assert fresh.resettable_by == frozenset(
        {ResetKind.TOOL_SWAP, ResetKind.WASH_CYCLE, ResetKind.OPERATOR_ASSERTION}
    )
    assert [(r.carrier_id, r.grade, r.operator) for r in new.resets] == [
        ("spreader", EvidenceGrade.OBSERVED, False),
        ("spreader_2", EvidenceGrade.OBSERVED, False),
    ]
    assert len(new.contacts) == 3  # edges through the retired carrier stay for history
    assert new.acquisitions["spreader"]
    assert {d.rule_id for d in deltas} == {"tool_swap"}


def test_surface_swap_rebinds_zone(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    new = fold(
        s,
        [ev("SURFACE_SWAP", 400, retired="board", introduced="board_2", from_zone="clean_stock")],
        cfg,
    )
    assert new.station.zones["work"].bound_carrier == "board_2"
    assert new.station.carriers["board_2"].kind == CarrierKind.SURFACE
    assert new.station.carriers["board_2"].home_zone == "work"
    # and the rebound zone is live: the next contact lands on the new surface
    new = fold(new, [zone_entry(500, "gloves", "work")], cfg)
    assert new.station.carriers["board_2"].taints["PINE_NUT"].hops == 1


def test_swap_with_unknown_retired_still_introduces(state: WorldState, cfg: Config) -> None:
    new = fold(
        state,
        [ev("SURFACE_SWAP", 400, retired="ghost", introduced="mat", from_zone="clean_stock")],
        cfg,
    )
    mat = new.station.carriers["mat"]
    assert mat.kind == CarrierKind.SURFACE and mat.home_zone is None
    assert [r.carrier_id for r in new.resets] == ["mat"]


def test_swap_onto_existing_carrier_resets_it(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    new = fold(
        s,
        [ev("TOOL_SWAP", 400, retired="spreader", introduced="board", from_zone="clean_stock")],
        cfg,
    )
    assert new.station.carriers["board"].taints == {}
    assert new.station.carriers["board"].kind == CarrierKind.SURFACE


# -- WASH_CYCLE ---------------------------------------------------------------------------


def test_wash_cycle_clears_at_asserted_grade(state: WorldState, cfg: Config) -> None:
    s = dirty(state, cfg)
    e = ev("WASH_CYCLE", 400, carrier="spreader", zone="wash", duration_ms=5000)
    new, deltas = reduce(s, e, cfg)
    sp = new.station.carriers["spreader"]
    assert sp.taints == {}
    assert sp.clean_grade == EvidenceGrade.ASSERTED
    assert sp.asserted_at == 400
    assert sp.epistemic == EpistemicStatus.TRACKED and sp.last_observed_at == 400
    assert new.resets[-1].grade == EvidenceGrade.ASSERTED and new.resets[-1].operator is False
    assert {d.rule_id for d in deltas} == {"wash_cycle"}


# -- OPERATOR_ASSERTION -------------------------------------------------------------------


def test_operator_assertion_clears_without_touching_epistemic(
    state: WorldState, cfg: Config
) -> None:
    s = dirty(state, cfg)
    s = fold(
        s,
        [
            ev(
                "CARRIER_OBSERVABILITY_CHANGED",
                350,
                carrier="spreader",
                epistemic="UNKNOWN",
                cause="occluded",
            )
        ],
        cfg,
    )
    for claim in ("CLEAN", "REPLACED"):
        e = ev("OPERATOR_ASSERTION", 400, carrier="spreader", claim=claim, worker_slot=0)
        new, deltas = reduce(s, e, cfg)
        sp = new.station.carriers["spreader"]
        assert sp.taints == {}
        assert sp.clean_grade == EvidenceGrade.ASSERTED and sp.asserted_at == 400
        assert sp.epistemic == EpistemicStatus.UNKNOWN  # an assertion never upgrades trust
        assert sp.last_observed_at == 300  # unchanged: last seen at the board contact
        assert new.resets[-1].grade == EvidenceGrade.ASSERTED and new.resets[-1].operator is True
        assert {d.rule_id for d in deltas} == {"operator_assertion"}


def test_reset_on_unknown_carrier_is_rejected(state: WorldState, cfg: Config) -> None:
    for e in (
        ev("OPERATOR_ASSERTION", 400, carrier="ghost", claim="CLEAN", worker_slot=0),
        ev("WASH_CYCLE", 400, carrier="ghost", zone="wash", duration_ms=1),
    ):
        new, deltas = reduce(state, e, cfg)
        assert new is state and deltas == []


# -- FOOD is never reset (11 inv. 7) -----------------------------------------------------


def test_food_carrier_is_never_cleared(bound_ticket: WorldState, cfg: Config) -> None:
    s = fold(
        bound_ticket,
        [
            ev("TICKET_PREP_STARTED", 30, ticket="T1"),
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "food:T1"),
        ],
        cfg,
    )
    assert "PINE_NUT" in s.station.carriers["food:T1"].taints
    for e in (
        ev("OPERATOR_ASSERTION", 300, carrier="food:T1", claim="CLEAN", worker_slot=0),
        ev("WASH_CYCLE", 300, carrier="food:T1", zone="wash", duration_ms=1),
        ev("TOOL_SWAP", 300, retired="food:T1", introduced="food:T1b", from_zone="clean_stock"),
        glove_don(300),
    ):
        new, _ = reduce(s, e, cfg)
        assert "PINE_NUT" in new.station.carriers["food:T1"].taints
        assert all(r.carrier_id != "food:T1" for r in new.resets)
