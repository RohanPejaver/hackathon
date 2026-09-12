"""Precondition check -> Tier 0 (15 §1): recipe-scoped, unrestricted silence, PROTOCOL_ONLY,
STALE by time, closure matching."""

from src.domain import EpistemicStatus, Mode, Resolution
from src.knowledge import UNKNOWN_ALLERGEN_PROFILE, KnowledgeProvider
from src.risk import check_preconditions, pessimistic_allergens, required_carriers
from tests.unit.risk.builders import carrier, cfg, demo_station, knowledge, state, taint, ticket

ZONE_CARRIERS = ["bin:bread", "bin:turkey", "bin:mayo", "board", "landing"]


def test_required_carriers_are_recipe_scoped_gloves_and_tools_first() -> None:
    kp = KnowledgeProvider(knowledge())
    required = required_carriers(state(), ticket(), kp)
    assert required[:2] == ["gloves", "spreader"]
    assert required[2:] == ZONE_CARRIERS
    assert "bin:pesto" not in required


def test_protocol_only_every_required_carrier_is_listed() -> None:
    s = state(demo_station(mode=Mode.PROTOCOL_ONLY, epistemic=EpistemicStatus.UNKNOWN))
    blocking = check_preconditions(s, ticket(), knowledge(), cfg())
    assert blocking == ["gloves", "spreader", *ZONE_CARRIERS]


def test_tainted_pesto_bin_is_not_in_a_turkey_sandwich_checklist() -> None:
    s = state(
        demo_station(
            epistemic=EpistemicStatus.UNKNOWN,
            carriers={"bin:pesto": carrier("bin:pesto", taints={"PINE_NUT": taint("PINE_NUT", 0)})},
        )
    )
    assert "bin:pesto" not in check_preconditions(s, ticket(), knowledge(), cfg())


def test_unrestricted_ticket_is_silent_even_when_everything_is_unknown() -> None:
    s = state(demo_station(mode=Mode.PROTOCOL_ONLY, epistemic=EpistemicStatus.UNKNOWN))
    assert check_preconditions(s, ticket(allergens=()), knowledge(), cfg()) == []
    ambiguous = ticket(allergens=("PINE_NUT",), resolution=Resolution.AMBIGUOUS)
    assert check_preconditions(s, ambiguous, knowledge(), cfg()) == []


def test_only_matching_taints_block_when_tracked() -> None:
    s = state(
        demo_station(
            carriers={
                "gloves": carrier("gloves", taints={"PINE_NUT": taint("PINE_NUT", 0)}),
                "spreader": carrier("spreader", taints={"TREE_NUT": taint("TREE_NUT", 0, hops=1)}),
                "board": carrier("board", taints={"ALMOND": taint("ALMOND", 0)}),
                "bin:mayo": carrier("bin:mayo", taints={"EGG": taint("EGG", 0)}),
            }
        )
    )
    assert check_preconditions(s, ticket(), knowledge(), cfg()) == ["gloves", "spreader"]


def test_unknown_allergen_profile_taint_blocks_any_restriction() -> None:
    s = state(
        demo_station(
            carriers={
                "board": carrier(
                    "board", taints={UNKNOWN_ALLERGEN_PROFILE: taint(UNKNOWN_ALLERGEN_PROFILE, 0)}
                )
            }
        )
    )
    assert check_preconditions(s, ticket(allergens=("EGG",)), knowledge(), cfg()) == ["board"]


def test_stale_by_time_uses_effective_epistemic() -> None:
    # gloves decay after 20s, surfaces after 300s: at t=30s only gloves are STALE.
    s = state(demo_station(t=0), t=30_000)
    assert check_preconditions(s, ticket(), knowledge(), cfg()) == ["gloves"]
    # at t=400s tools (120s) and surfaces (300s) have aged out too; containers (600s) not yet
    s2 = state(demo_station(t=0), t=400_000)
    assert check_preconditions(s2, ticket(), knowledge(), cfg()) == [
        "gloves",
        "spreader",
        "board",
        "landing",
    ]
    s3 = state(demo_station(t=0), t=700_000)
    assert check_preconditions(s3, ticket(), knowledge(), cfg()) == [
        "gloves",
        "spreader",
        *ZONE_CARRIERS,
    ]


def test_never_observed_tracked_flag_still_counts_as_unknown() -> None:
    s = state(demo_station(observed=False))
    assert "gloves" in check_preconditions(s, ticket(), knowledge(), cfg())


def test_pessimistic_closure_is_scoped_to_the_restriction_and_window() -> None:
    s = state(
        demo_station(t=100_000, recent={"PINE_NUT": 90_000, "EGG": 95_000, "TREE_NUT": 1_000}),
        t=100_000,
    )
    restricted = KnowledgeProvider(knowledge()).closure("PINE_NUT")
    assert pessimistic_allergens(s, restricted, cfg(station_recent_window=50_000)) == frozenset(
        {"PINE_NUT"}
    )
    assert pessimistic_allergens(s, restricted, cfg()) == frozenset({"PINE_NUT", "TREE_NUT"})


def test_reset_since_bind_satisfies_a_non_tracked_carrier() -> None:
    """With no perception nothing is ever TRACKED (PROTOCOL_ONLY); the protocol question is
    whether a valid reset happened since the bind (03 D, 37 beat 4). A reset before the bind
    does not count, so every restricted bind asks again (10)."""
    from src.domain import EvidenceGrade, ResetRecord

    s = state(demo_station(mode=Mode.PROTOCOL_ONLY, epistemic=EpistemicStatus.UNKNOWN))
    bound = ticket().model_copy(update={"bound_at": 1000})
    before = ResetRecord(
        event_id="a0",
        t_occurred=500,
        carrier_id="gloves",
        grade=EvidenceGrade.ASSERTED,
        operator=True,
    )
    after = ResetRecord(
        event_id="a1",
        t_occurred=1500,
        carrier_id="gloves",
        grade=EvidenceGrade.ASSERTED,
        operator=True,
    )
    assert "gloves" in check_preconditions(
        s.model_copy(update={"resets": [before]}), bound, knowledge(), cfg()
    )
    assert "gloves" not in check_preconditions(
        s.model_copy(update={"resets": [after]}), bound, knowledge(), cfg()
    )
    assert "spreader" in check_preconditions(
        s.model_copy(update={"resets": [after]}), bound, knowledge(), cfg()
    )


def test_reset_since_bind_does_not_excuse_a_matching_taint() -> None:
    from src.domain import EvidenceGrade, ResetRecord

    s = state(
        demo_station(
            mode=Mode.PROTOCOL_ONLY,
            epistemic=EpistemicStatus.UNKNOWN,
            carriers={"gloves": carrier("gloves", taints={"PINE_NUT": taint("PINE_NUT", 2000)})},
        )
    )
    bound = ticket().model_copy(update={"bound_at": 1000})
    after = ResetRecord(
        event_id="a1",
        t_occurred=1500,
        carrier_id="gloves",
        grade=EvidenceGrade.ASSERTED,
        operator=True,
    )
    assert "gloves" in check_preconditions(
        s.model_copy(update={"resets": [after]}), bound, knowledge(), cfg()
    )
