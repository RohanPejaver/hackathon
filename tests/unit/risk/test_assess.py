"""assess(): level selection, provenance fields, MULTI_RESTRICTION, operator resolution."""

import enum
import inspect
import re
from pathlib import Path

from src.domain import EpistemicStatus, EvidenceGrade, Mode, RiskLevel, TicketLifecycle
from src.risk import assess
from tests.unit.risk.builders import (
    carrier,
    cfg,
    demo_station,
    edge,
    food,
    knowledge,
    reset,
    state,
    taint,
    ticket,
)

ROOT = Path(__file__).resolve().parents[3]


def _prep_state(contacts, resets=(), tid="T48", t=10_000, **station):
    return state(
        demo_station(t=t, extra=[food(tid)], **station),
        t=t,
        contacts=list(contacts),
        resets=list(resets),
        last_event_id="e-cause",
        last_event_type="TICKET_PREP_STARTED",
    )


def test_bound_ticket_with_tainted_carriers_is_unverified_with_taint_grade() -> None:
    s = state(
        demo_station(
            carriers={
                "gloves": carrier(
                    "gloves",
                    taints={"PINE_NUT": taint("PINE_NUT", 0, grade=EvidenceGrade.INFERRED)},
                )
            }
        ),
        t=1000,
        last_event_id="e-bind",
        last_event_type="TICKET_BOUND",
    )
    [a] = assess(s, [ticket()], knowledge(), cfg())
    assert a.level == RiskLevel.UNVERIFIED
    assert a.blocking_carriers == ["gloves"]
    assert a.max_grade == EvidenceGrade.INFERRED
    assert a.pathways == []
    assert (a.assessed_at, a.cause_event_id, a.cause_event_type) == (1000, "e-bind", "TICKET_BOUND")
    assert (a.ticket_lifecycle, a.station_id, a.mode) == (
        TicketLifecycle.BOUND,
        "demo-bagel",
        Mode.FULL,
    )
    assert (a.config_version, a.knowledge_version) == ("1", "1")


def test_unverified_from_epistemic_only_is_pessimistic() -> None:
    s = state(demo_station(mode=Mode.PROTOCOL_ONLY, epistemic=EpistemicStatus.UNKNOWN))
    [a] = assess(s, [ticket()], knowledge(), cfg())
    assert a.level == RiskLevel.UNVERIFIED and a.max_grade == EvidenceGrade.PESSIMISTIC
    assert len(a.blocking_carriers) == 7


def test_clear_is_not_a_safety_claim_just_no_pathway() -> None:
    [a] = assess(state(), [ticket()], knowledge(), cfg())
    assert a.level == RiskLevel.CLEAR
    assert a.blocking_carriers == [] and a.pathways == []
    assert a.max_grade == EvidenceGrade.OBSERVED
    assert a.operator_resolution is False and a.resolution_reason is None


def test_clear_reports_operator_resolution_from_the_latest_reset_on_required_carriers() -> None:
    s = state(
        resets=[
            reset("r1", 500, "gloves"),
            reset("r2", 900, "spreader", EvidenceGrade.ASSERTED, operator=True),
        ],
        t=1000,
    )
    [a] = assess(s, [ticket()], knowledge(), cfg())
    assert a.level == RiskLevel.CLEAR and a.operator_resolution
    assert a.resolution_reason == "RESOLVED_BY_ASSERTION"
    s2 = state(
        resets=[
            reset("r2", 900, "spreader", EvidenceGrade.ASSERTED, operator=True),
            reset("r1", 950, "gloves"),
        ],
        t=1000,
    )
    [a2] = assess(s2, [ticket()], knowledge(), cfg())
    assert not a2.operator_resolution and a2.resolution_reason == "RESOLVED_BY_RESET"


def test_open_pathway_in_prep_and_checklist_coexist() -> None:
    s = _prep_state(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", "food:T48")],
        carriers={
            "gloves": carrier(
                "gloves", t_observed=10_000, taints={"PINE_NUT": taint("PINE_NUT", 1000, "e1")}
            )
        },
    )
    [a] = assess(s, [ticket(lifecycle=TicketLifecycle.IN_PREP)], knowledge(), cfg())
    assert a.level == RiskLevel.PATHWAY_OPEN
    assert a.max_grade == EvidenceGrade.OBSERVED
    assert [p.nodes for p in a.pathways] == [["bin:pesto", "gloves", "food:T48"]] * 2
    assert a.blocking_carriers == ["gloves"]
    assert a.resolution_reason is None


def test_bound_ticket_never_searches_pathways() -> None:
    s = _prep_state(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", "food:T48")]
    )
    [a] = assess(s, [ticket(lifecycle=TicketLifecycle.BOUND)], knowledge(), cfg())
    assert a.level == RiskLevel.CLEAR and a.pathways == []


def test_pathway_resolved_by_reset_and_by_assertion() -> None:
    contacts = [edge("e1", 1000, "gloves", "bin:pesto"), edge("e3", 3000, "gloves", "food:T48")]
    by_reset = _prep_state(contacts, resets=[reset("r2", 2000, "gloves")])
    [a] = assess(by_reset, [ticket(lifecycle=TicketLifecycle.IN_PREP)], knowledge(), cfg())
    assert a.level == RiskLevel.PATHWAY_RESOLVED
    assert a.resolution_reason == "RESOLVED_BY_RESET" and not a.operator_resolution
    assert all(p.broken for p in a.pathways)
    by_assertion = _prep_state(
        contacts, resets=[reset("r2", 2000, "gloves", EvidenceGrade.ASSERTED, operator=True)]
    )
    [b] = assess(by_assertion, [ticket(lifecycle=TicketLifecycle.COMPLETE)], knowledge(), cfg())
    assert b.level == RiskLevel.PATHWAY_RESOLVED
    assert b.resolution_reason == "RESOLVED_BY_ASSERTION" and b.operator_resolution


def test_max_grade_over_open_pathways_only() -> None:
    s = _prep_state(
        [
            edge("e1", 1000, "gloves", "bin:pesto"),
            edge("e2", 2000, "gloves", "spreader", EvidenceGrade.INFERRED),
            edge("e3", 3000, "spreader", "food:T48"),
        ]
    )
    [a] = assess(s, [ticket(lifecycle=TicketLifecycle.IN_PREP)], knowledge(), cfg())
    assert a.level == RiskLevel.PATHWAY_OPEN and a.max_grade == EvidenceGrade.INFERRED


def test_one_assessment_per_restricted_allergen_sorted() -> None:
    out = assess(state(), [ticket(allergens=("PINE_NUT", "EGG"))], knowledge(), cfg())
    assert [a.allergen_id for a in out] == ["EGG", "PINE_NUT"]


def test_inactive_and_unrestricted_tickets_are_skipped() -> None:
    tickets = [
        ticket("T1", lifecycle=TicketLifecycle.RECEIVED),
        ticket("T2", lifecycle=TicketLifecycle.VOIDED),
        ticket("T3", lifecycle=TicketLifecycle.RELEASED),
        ticket("T4", allergens=()),
        ticket("T5", lifecycle=TicketLifecycle.HELD),
    ]
    assert [a.ticket_id for a in assess(state(), tickets, knowledge(), cfg())] == ["T5"]


def test_multi_restriction_condition_adds_a_tier0_assessment_per_ticket() -> None:
    s = state(conditions=["MULTI_RESTRICTION"])
    out = assess(s, [ticket("T1"), ticket("T2", allergens=("EGG",))], knowledge(), cfg())
    multis = [a for a in out if a.condition == "MULTI_RESTRICTION"]
    assert [(a.ticket_id, a.allergen_id) for a in multis] == [("T1", "PINE_NUT"), ("T2", "EGG")]
    assert all(a.level == RiskLevel.UNVERIFIED and a.blocking_carriers == [] for a in multis)
    assert all(a.max_grade == EvidenceGrade.OBSERVED for a in multis)


def test_assess_is_deterministic() -> None:
    s = _prep_state(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", "food:T48")]
    )
    t = [ticket(lifecycle=TicketLifecycle.IN_PREP)]
    a = assess(s, t, knowledge(), cfg())
    b = assess(s, t, knowledge(), cfg())
    assert [x.model_dump_json() for x in a] == [x.model_dump_json() for x in b]


def test_no_enum_has_a_safe_member() -> None:
    import src.domain.models
    import src.knowledge.provider
    import src.policy.build
    import src.policy.evaluate
    import src.policy.state
    import src.risk.assess
    import src.risk.pathways
    import src.risk.preconditions

    modules = [
        src.domain.models,
        src.knowledge.provider,
        src.risk.assess,
        src.risk.pathways,
        src.risk.preconditions,
        src.policy.build,
        src.policy.evaluate,
        src.policy.state,
    ]
    for module in modules:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, enum.Enum):
                assert "SAFE" not in obj.__members__, obj
    for package in ("domain", "risk", "policy", "knowledge"):
        for file in (ROOT / "src" / package).rglob("*.py"):
            assert not re.search(r"^\s*SAFE\s*=", file.read_text(), re.M), file
