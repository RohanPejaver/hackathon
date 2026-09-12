"""13 §Transition table: ZONE_ENTRY acquisition and CONTACT_BEGIN propagation."""

from __future__ import annotations

from src.domain import Config, EpistemicStatus, EvidenceGrade, Strength, WorldState
from src.state import reduce
from tests.unit.state.conftest import contact, ev, fold, glove_don, make_config, zone_entry


def taint(state: WorldState, carrier: str, allergen: str):  # type: ignore[no-untyped-def]
    return state.station.carriers[carrier].taints[allergen]


def taints(state: WorldState, carrier: str) -> set[str]:
    return set(state.station.carriers[carrier].taints)


# -- ZONE_ENTRY ---------------------------------------------------------------------------


def test_zone_entry_into_ingredient_zone_acquires_profile_at_hop_zero(
    state: WorldState, cfg: Config
) -> None:
    e = zone_entry(100, "gloves", "bin:pesto")
    new, deltas = reduce(state, e, cfg)
    gloves = new.station.carriers["gloves"]
    assert set(gloves.taints) == {"MILK", "PINE_NUT"}
    r = gloves.taints["PINE_NUT"]
    assert r.hops == 0
    assert r.grade == EvidenceGrade.OBSERVED
    assert r.strength == Strength.PRESENT
    assert r.acquired_at == 100
    assert r.source_event_id == e.event_id
    assert r.source_carrier_id == "bin:pesto"
    assert gloves.epistemic == EpistemicStatus.TRACKED
    assert gloves.last_observed_at == 100
    assert new.station.recent_allergen_exposure == {"MILK": 100, "PINE_NUT": 100}
    assert new.acquisitions["gloves"] == [gloves.taints["MILK"], gloves.taints["PINE_NUT"]]
    assert {d.rule_id for d in deltas} >= {"zone_acquire", "observation", "contact_edge"}
    assert new.event_ids == [e.event_id]
    assert new.t_occurred == 100
    assert new.last_event_type == "ZONE_ENTRY"
    assert new.last_event_id == e.event_id
    assert new.last_event_source == "PERCEPTION"
    assert new.deltas == deltas
    assert state.station.carriers["gloves"].taints == {}  # input untouched


def test_zone_entry_grade_follows_event_grade(state: WorldState, cfg: Config) -> None:
    new = fold(state, [zone_entry(100, "gloves", "bin:pesto", grade="INFERRED")], cfg)
    assert taint(new, "gloves", "PINE_NUT").grade == EvidenceGrade.INFERRED


def test_zone_entry_possible_strength_from_profile(cfg: Config) -> None:
    from src.state import initial
    from tests.unit.state.conftest import make_station

    st = make_station()
    st = st.model_copy(
        update={"zone_allergens": {**st.zone_allergens, "bin:pesto": {"TREE_NUT": "POSSIBLE"}}}
    )
    s = initial(cfg, st)
    new = fold(s, [zone_entry(100, "gloves", "bin:pesto")], cfg)
    assert taint(new, "gloves", "TREE_NUT").strength == Strength.POSSIBLE


def test_zone_entry_contacts_bound_container_back_contamination(
    state: WorldState, cfg: Config
) -> None:
    """ADR-0008: a tainted hand entering the shared mayo tub taints the tub (hop 1)."""
    new = fold(
        state, [zone_entry(100, "gloves", "bin:pesto"), zone_entry(200, "gloves", "bin:mayo")], cfg
    )
    mayo = new.station.carriers["bin:mayo"]
    assert mayo.taints["PINE_NUT"].hops == 1
    assert mayo.taints["PINE_NUT"].source_carrier_id == "gloves"
    assert "EGG" not in mayo.taints  # the tub is the source of EGG, it does not acquire it
    assert taint(new, "gloves", "EGG").hops == 0
    assert [(c.a, c.b) for c in new.contacts] == [("gloves", "bin:pesto"), ("gloves", "bin:mayo")]


def test_fresh_gloves_pick_up_back_contamination_from_tub(state: WorldState, cfg: Config) -> None:
    new = fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            zone_entry(200, "gloves", "bin:mayo"),
            glove_don(300),
            zone_entry(400, "gloves", "bin:mayo"),
        ],
        cfg,
    )
    gloves = new.station.carriers["gloves"]
    assert gloves.taints["PINE_NUT"].hops == 2
    assert gloves.taints["PINE_NUT"].source_carrier_id == "bin:mayo"
    assert gloves.taints["EGG"].hops == 0


def test_zone_entry_into_work_zone_propagates_to_bound_surface(
    state: WorldState, cfg: Config
) -> None:
    new = fold(
        state, [zone_entry(100, "gloves", "bin:pesto"), zone_entry(200, "gloves", "work")], cfg
    )
    assert taint(new, "board", "PINE_NUT").hops == 1
    assert new.station.recent_allergen_exposure == {"MILK": 100, "PINE_NUT": 100}


def test_zone_entry_into_zone_without_bound_carrier_is_observation_only(
    state: WorldState, cfg: Config
) -> None:
    new, deltas = reduce(state, zone_entry(100, "gloves", "glove_dispenser"), cfg)
    assert new.station.carriers["gloves"].taints == {}
    assert new.station.carriers["gloves"].epistemic == EpistemicStatus.TRACKED
    assert new.contacts == []
    assert {d.rule_id for d in deltas} == {"observation"}


def test_zone_entry_unknown_zone_or_carrier_is_rejected(state: WorldState, cfg: Config) -> None:
    for e in (zone_entry(100, "gloves", "bin:nope"), zone_entry(100, "ghost", "bin:pesto")):
        new, deltas = reduce(state, e, cfg)
        assert new is state
        assert deltas == []


def test_zone_entry_keeps_earlier_hop_zero_record(state: WorldState, cfg: Config) -> None:
    first = zone_entry(100, "gloves", "bin:pesto")
    new = fold(state, [first, zone_entry(500, "gloves", "bin:pesto")], cfg)
    r = taint(new, "gloves", "PINE_NUT")
    assert r.acquired_at == 100 and r.source_event_id == first.event_id
    assert len(new.acquisitions["gloves"]) == 2  # only records actually stored
    assert new.station.recent_allergen_exposure["PINE_NUT"] == 500


# -- CONTACT_BEGIN ------------------------------------------------------------------------


def test_contact_is_bidirectional_and_records_one_edge(state: WorldState, cfg: Config) -> None:
    c = contact(300, "gloves", "spreader")
    new = fold(
        state,
        [zone_entry(100, "gloves", "bin:pesto"), zone_entry(200, "spreader", "bin:mayo"), c],
        cfg,
    )
    assert taint(new, "spreader", "PINE_NUT").hops == 1
    assert taint(new, "spreader", "PINE_NUT").source_carrier_id == "gloves"
    assert taint(new, "gloves", "EGG").hops == 1
    assert taint(new, "gloves", "EGG").source_carrier_id == "spreader"
    assert taint(new, "spreader", "EGG").hops == 0  # its own record untouched
    edges = [x for x in new.contacts if x.event_id == c.event_id]
    assert len(edges) == 1
    assert (edges[0].a, edges[0].b, edges[0].grade) == (
        "gloves",
        "spreader",
        EvidenceGrade.OBSERVED,
    )
    for cid in ("gloves", "spreader"):
        assert new.station.carriers[cid].last_observed_at == 300
        assert new.station.carriers[cid].epistemic == EpistemicStatus.TRACKED


def test_propagation_grade_is_minimum_along_the_edge(state: WorldState, cfg: Config) -> None:
    new = fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto", grade="OBSERVED"),
            contact(200, "gloves", "spreader", grade="INFERRED"),
            contact(300, "spreader", "board", grade="OBSERVED"),
        ],
        cfg,
    )
    assert taint(new, "spreader", "PINE_NUT").grade == EvidenceGrade.INFERRED
    assert taint(new, "board", "PINE_NUT").grade == EvidenceGrade.INFERRED  # never upgraded


def test_strength_decays_per_hop(state: WorldState, cfg: Config) -> None:
    new = fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "spreader"),
            contact(300, "spreader", "board"),
            contact(400, "board", "landing"),
        ],
        cfg,
    )
    assert taint(new, "gloves", "PINE_NUT").strength == Strength.PRESENT  # hop 0
    assert taint(new, "spreader", "PINE_NUT").strength == Strength.PRESENT  # hop 1
    assert taint(new, "board", "PINE_NUT").strength == Strength.POSSIBLE  # hop 2
    assert taint(new, "landing", "PINE_NUT").strength == Strength.POSSIBLE  # hop 3


def test_possible_source_never_rises(cfg: Config) -> None:
    from src.state import initial
    from tests.unit.state.conftest import make_station

    st = make_station()
    st = st.model_copy(update={"zone_allergens": {"bin:pesto": {"TREE_NUT": "POSSIBLE"}}})
    new = fold(
        initial(cfg, st),
        [zone_entry(100, "gloves", "bin:pesto"), contact(200, "gloves", "spreader")],
        cfg,
    )
    assert taint(new, "spreader", "TREE_NUT").strength == Strength.POSSIBLE


def test_propagation_halts_at_max_hops(state: WorldState) -> None:
    cfg = make_config(max_hops=2)
    new = fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "spreader"),  # hop 1
            contact(300, "spreader", "board"),  # hop 2
            contact(400, "board", "landing"),  # would be hop 3: halts
        ],
        cfg,
    )
    assert taint(new, "board", "PINE_NUT").hops == 2
    assert "PINE_NUT" not in taints(new, "landing")
    assert all(r.hops <= 2 for c in new.station.carriers.values() for r in c.taints.values())
    assert len(new.contacts) == 4  # the edge is still evidence


def test_keep_fewer_hops_replace_more_hops(state: WorldState, cfg: Config) -> None:
    new = fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "spreader"),  # spreader hop 1
            contact(300, "spreader", "board"),  # board hop 2
            contact(400, "gloves", "board"),  # board hop 1 -> replaces
            contact(500, "spreader", "board"),  # hop 2 again -> kept at 1
        ],
        cfg,
    )
    r = taint(new, "board", "PINE_NUT")
    assert r.hops == 1 and r.acquired_at == 400 and r.source_carrier_id == "gloves"
    pine = [x.hops for x in new.acquisitions["board"] if x.allergen_id == "PINE_NUT"]
    assert pine == [2, 1]


def test_contact_with_zone_id_resolves_to_bound_carrier(state: WorldState, cfg: Config) -> None:
    new = fold(state, [zone_entry(100, "gloves", "bin:pesto"), contact(200, "gloves", "work")], cfg)
    assert taint(new, "board", "PINE_NUT").hops == 1
    assert new.contacts[-1].b == "board"


def test_contact_with_landing_zone_reaches_in_prep_food(
    bound_ticket: WorldState, cfg: Config
) -> None:
    new = fold(
        bound_ticket,
        [
            ev("TICKET_PREP_STARTED", 30, ticket="T1"),
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "landing"),
        ],
        cfg,
    )
    assert taint(new, "landing", "PINE_NUT").hops == 1
    assert taint(new, "food:T1", "PINE_NUT").hops == 1
    pairs = {(c.a, c.b) for c in new.contacts if c.t_occurred == 200}
    assert pairs == {("gloves", "landing"), ("gloves", "food:T1")}


def test_contact_with_unknown_ids_is_rejected(state: WorldState, cfg: Config) -> None:
    for a, b in (("gloves", "ghost"), ("ghost", "gloves"), ("gloves", "tool_rack")):
        new, deltas = reduce(state, contact(100, a, b), cfg)
        assert new is state and deltas == []


def test_self_contact_changes_nothing_but_is_applied(state: WorldState, cfg: Config) -> None:
    new, deltas = reduce(state, contact(100, "gloves", "gloves"), cfg)
    assert new.contacts == []
    assert {d.rule_id for d in deltas} == {"observation"}


def test_taint_does_not_decay_with_time(state: WorldState, cfg: Config) -> None:
    new = fold(
        state,
        [zone_entry(100, "gloves", "bin:pesto"), zone_entry(100 + 10**9, "gloves", "work")],
        cfg,
    )
    assert "PINE_NUT" in taints(new, "gloves")
    assert taint(new, "board", "PINE_NUT").hops == 1
