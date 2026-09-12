"""Pathway search (33 §Risk engine): direct, tool, surface, back-contamination, hop limit,
reset-breaks-path, temporal ordering."""

from src.domain import EvidenceGrade, Strength
from src.risk import breaking_resets, find_pathways
from tests.unit.risk.builders import cfg, demo_station, edge, food, reset, state

PINE = frozenset({"PINE_NUT", "TREE_NUT"})
FOOD = "food:T48"


def _state(contacts, resets=(), acquisitions=None, t=10_000):
    return state(
        demo_station(t=t, extra=[food("T48")]),
        t=t,
        contacts=list(contacts),
        resets=list(resets),
        acquisitions=acquisitions,
    )


def _open(pathways):
    return [p for p in pathways if not p.broken]


def test_direct_hand_from_bin_onto_food() -> None:
    s = _state([edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", FOOD)])
    found = find_pathways(s, FOOD, PINE, cfg())
    open_ = _open(found)
    assert [p.nodes for p in open_] == [["bin:pesto", "gloves", FOOD]] * 2
    p = next(p for p in open_ if p.allergen_id == "PINE_NUT")
    assert p.event_ids == ["e1", "e2"]
    assert p.hops == 1
    assert p.grade == EvidenceGrade.OBSERVED
    assert p.strength == Strength.PRESENT
    tree = next(p for p in open_ if p.allergen_id == "TREE_NUT")
    assert tree.strength == Strength.POSSIBLE  # may_contain never rises


def test_food_entering_the_bin_is_a_zero_hop_pathway() -> None:
    s = _state([edge("e1", 1000, FOOD, "bin:pesto")])
    p = _open(find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg()))
    assert len(p) == 1 and p[0].nodes == ["bin:pesto", FOOD] and p[0].hops == 0


def test_tool_mediated() -> None:
    s = _state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "spreader"),
            edge("e3", 3000, "spreader", FOOD),
        ]
    )
    p = _open(find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg()))
    assert [x.nodes for x in p] == [["bin:pesto", "gloves", "spreader", FOOD]]
    assert p[0].hops == 2 and p[0].event_ids == ["e1", "e2", "e3"]
    assert p[0].strength == Strength.POSSIBLE  # decay at hop 2


def test_surface_mediated_scenario_c_three_edges_within_max_hops() -> None:
    s = _state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "board"),
            edge("e3", 3000, "board", FOOD),
        ]
    )
    p = _open(find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg(max_hops=3)))
    assert [x.nodes for x in p] == [["bin:pesto", "gloves", "board", FOOD]]
    assert p[0].grade == EvidenceGrade.OBSERVED and not p[0].broken


def test_hop_limit_four_edge_chain_not_found_at_three() -> None:
    contacts = [
        edge("e1", 1000, "gloves", "bin:pesto"),
        edge("e2", 2000, "gloves", "spreader"),
        edge("e3", 3000, "spreader", "board"),
        edge("e4", 4000, "board", FOOD),
    ]
    assert find_pathways(_state(contacts), FOOD, PINE, cfg(max_hops=3)) == []
    found = _open(find_pathways(_state(contacts), FOOD, frozenset({"PINE_NUT"}), cfg(max_hops=4)))
    assert [p.nodes for p in found] == [["bin:pesto", "gloves", "spreader", "board", FOOD]]


def test_reset_between_contacts_breaks_the_path_and_is_still_reported() -> None:
    s = _state(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e3", 3000, "gloves", FOOD)],
        resets=[reset("r1", 2000, "gloves")],
    )
    found = find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())
    assert len(found) == 1 and found[0].broken
    assert [r.event_id for r in breaking_resets(s, found[0])] == ["r1"]
    assert not breaking_resets(s, found[0])[0].operator


def test_reset_after_the_food_contact_does_not_break_but_assertion_does() -> None:
    contacts = [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", FOOD)]
    observed = _state(contacts, resets=[reset("r1", 3000, "gloves")])
    assert not find_pathways(observed, FOOD, frozenset({"PINE_NUT"}), cfg())[0].broken
    asserted = _state(
        contacts, resets=[reset("r1", 3000, "gloves", EvidenceGrade.ASSERTED, operator=True)]
    )
    p = find_pathways(asserted, FOOD, frozenset({"PINE_NUT"}), cfg())[0]
    assert p.broken and breaking_resets(asserted, p)[0].operator


def test_reset_before_the_inbound_contact_does_not_break() -> None:
    s = _state(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", FOOD)],
        resets=[reset("r0", 500, "gloves")],
    )
    assert not find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())[0].broken


def test_temporal_ordering_contamination_after_food_contact_does_not_count() -> None:
    s = _state([edge("e1", 1000, "gloves", FOOD), edge("e2", 2000, "gloves", "bin:pesto")])
    assert find_pathways(s, FOOD, PINE, cfg()) == []


def test_equal_timestamps_are_not_strictly_ordered() -> None:
    s = _state([edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 1000, "gloves", FOOD)])
    assert find_pathways(s, FOOD, PINE, cfg()) == []


def test_back_contamination_container_becomes_a_source_for_a_later_pathway() -> None:
    # pesto -> gloves -> mayo tub; glove change; new gloves -> mayo tub -> food (scenario I)
    from tests.unit.risk.builders import taint

    s = _state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "bin:mayo"),
            edge("e4", 4000, "gloves", "bin:mayo"),
            edge("e5", 5000, "gloves", FOOD),
        ],
        resets=[reset("r3", 3000, "gloves")],
        acquisitions={
            "gloves": [taint("PINE_NUT", 1000, "e1", "bin:pesto")],
            "bin:mayo": [taint("PINE_NUT", 2000, "e2", "gloves", hops=1)],
        },
    )
    found = find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())
    open_ = _open(found)
    assert [p.nodes for p in open_] == [["bin:mayo", "gloves", FOOD]]
    assert open_[0].event_ids == ["e4", "e5"] and open_[0].hops == 1
    assert open_[0].grade == EvidenceGrade.OBSERVED
    assert [p.nodes for p in found if p.broken] == [["bin:pesto", "gloves", FOOD]]


def test_container_asserted_clean_is_no_longer_a_source() -> None:
    from tests.unit.risk.builders import taint

    s = _state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "bin:mayo"),
            edge("e4", 4000, "gloves", "bin:mayo"),
            edge("e5", 5000, "gloves", FOOD),
        ],
        resets=[
            reset("r3", 3000, "gloves"),
            reset("r3b", 3500, "bin:mayo", EvidenceGrade.ASSERTED, operator=True),
        ],
        acquisitions={"bin:mayo": [taint("PINE_NUT", 2000, "e2", "gloves", hops=1)]},
    )
    assert _open(find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())) == []


def test_non_container_acquisitions_never_short_circuit_the_root() -> None:
    from tests.unit.risk.builders import taint

    s = _state(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", FOOD)],
        acquisitions={"gloves": [taint("PINE_NUT", 1000, "e1", "bin:pesto")]},
    )
    p = _open(find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg()))
    assert [x.nodes for x in p] == [["bin:pesto", "gloves", FOOD]]


def test_grade_is_minimum_along_the_path() -> None:
    s = _state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "spreader", EvidenceGrade.INFERRED),
            edge("e3", 3000, "spreader", FOOD),
        ]
    )
    assert find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())[0].grade == EvidenceGrade.INFERRED


def test_re_entry_is_one_pathway_not_n_and_output_is_deterministic() -> None:
    s = _state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "spreader"),
            edge("e3", 3000, "spreader", FOOD),
            edge("e4", 4000, "spreader", FOOD),
            edge("e5", 5000, "spreader", FOOD),
        ]
    )
    a = find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())
    b = find_pathways(s, FOOD, frozenset({"PINE_NUT"}), cfg())
    assert a == b
    assert [p.nodes for p in a] == [["bin:pesto", "gloves", "spreader", FOOD]]


def test_no_allergens_or_no_edges_is_empty() -> None:
    assert find_pathways(_state([]), FOOD, PINE, cfg()) == []
    s = _state([edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", FOOD)])
    assert find_pathways(s, FOOD, frozenset(), cfg()) == []
    assert find_pathways(s, FOOD, frozenset({"EGG"}), cfg()) == []
