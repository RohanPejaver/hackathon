"""Policy tests (33): tier selection, alert_key dedup, escalation, cooldown, suppression."""

import pytest

from src.domain import AlertLifecycle, EvidenceGrade, Mode, RiskLevel, TicketLifecycle, Tier
from src.policy import (
    AlertState,
    alert_key,
    evaluate,
    multi_restriction_signature,
    pathway_signature,
    precondition_signature,
)
from tests.unit.policy.builders import STATION, assessment, pathway
from tests.unit.risk.builders import cfg

FOOD = "food:T48"
DIRECT = pathway(["bin:pesto", "gloves", FOOD])


def _apply(alerts: AlertState, commands):
    return [alerts.apply(c) for c in commands]


@pytest.mark.parametrize(
    ("level", "lifecycle", "grade", "mode", "tier"),
    [
        (RiskLevel.UNVERIFIED, TicketLifecycle.BOUND, EvidenceGrade.OBSERVED, Mode.FULL, 0),
        (RiskLevel.UNVERIFIED, TicketLifecycle.IN_PREP, EvidenceGrade.PESSIMISTIC, Mode.FULL, 0),
        (RiskLevel.PATHWAY_OPEN, TicketLifecycle.IN_PREP, EvidenceGrade.OBSERVED, Mode.FULL, 1),
        (RiskLevel.PATHWAY_OPEN, TicketLifecycle.COMPLETE, EvidenceGrade.OBSERVED, Mode.FULL, 2),
        (RiskLevel.PATHWAY_OPEN, TicketLifecycle.HELD, EvidenceGrade.OBSERVED, Mode.FULL, 2),
        (RiskLevel.PATHWAY_OPEN, TicketLifecycle.IN_PREP, EvidenceGrade.INFERRED, Mode.FULL, 0),
        (RiskLevel.PATHWAY_OPEN, TicketLifecycle.COMPLETE, EvidenceGrade.ASSERTED, Mode.FULL, 0),
        (
            RiskLevel.PATHWAY_OPEN,
            TicketLifecycle.IN_PREP,
            EvidenceGrade.OBSERVED,
            Mode.PROTOCOL_ONLY,
            0,
        ),
        (
            RiskLevel.PATHWAY_OPEN,
            TicketLifecycle.COMPLETE,
            EvidenceGrade.OBSERVED,
            Mode.PROTOCOL_ONLY,
            2,
        ),
        (RiskLevel.CLEAR, TicketLifecycle.IN_PREP, EvidenceGrade.OBSERVED, Mode.FULL, None),
        (
            RiskLevel.PATHWAY_RESOLVED,
            TicketLifecycle.COMPLETE,
            EvidenceGrade.OBSERVED,
            Mode.FULL,
            None,
        ),
    ],
)
def test_tier_table(level, lifecycle, grade, mode, tier) -> None:
    pathways = [pathway(["bin:pesto", "gloves", FOOD], grade=grade)] if "PATHWAY" in level else []
    if level == RiskLevel.PATHWAY_RESOLVED:
        pathways = [pathway(["bin:pesto", "gloves", FOOD], broken=True)]
    a = assessment(level, lifecycle=lifecycle, grade=grade, mode=mode, pathways=pathways)
    commands = evaluate([a], AlertState(cfg()), cfg())
    if tier is None:
        assert commands == []
    else:
        assert [c.kind for c in commands] == ["RAISE"]
        assert commands[0].alert.tier == Tier(tier)


def test_alert_identity_and_id_scheme() -> None:
    alerts = AlertState(cfg())
    [raise_cmd] = evaluate([assessment()], alerts, cfg())
    sig = precondition_signature("T48", "PINE_NUT")
    assert raise_cmd.alert.pathway_signature == sig
    assert raise_cmd.alert.alert_key == alert_key(STATION, sig) == f"{STATION}:{sig}"
    assert raise_cmd.alert.alert_id == "pending"
    assert (raise_cmd.t_occurred, raise_cmd.cause_event_id) == (1000, "e-cause")
    stored = alerts.apply(raise_cmd)
    assert stored.alert_id == "al-1" and stored.state == AlertLifecycle.RAISED
    [second] = evaluate([assessment(tid="T49")], alerts, cfg())
    assert alerts.apply(second).alert_id == "al-2"
    assert alerts.by_key(stored.alert_key) == stored


def test_dedup_same_assessment_twice_raises_once() -> None:
    alerts = AlertState(cfg())
    a = assessment(blocking=["gloves", "spreader"])
    first = evaluate([a], alerts, cfg())
    assert [c.kind for c in first] == ["RAISE"]
    _apply(alerts, first)
    assert evaluate([a], alerts, cfg()) == []
    assert evaluate([a.model_copy(update={"assessed_at": 5000})], alerts, cfg()) == []


def test_checklist_shrinks_as_an_update_not_a_new_alert() -> None:
    alerts = AlertState(cfg())
    _apply(alerts, evaluate([assessment(blocking=["gloves", "spreader"])], alerts, cfg()))
    [cmd] = evaluate([assessment(blocking=["spreader"], t=2000)], alerts, cfg())
    assert cmd.kind == "UPDATE"
    stored = alerts.apply(cmd)
    assert stored.alert_id == "al-1"
    assert stored.blocking_carriers == ["spreader"] and stored.updated_at == 2000
    # 26 §Tier 0: the line ticks off, it does not disappear (done = not in blocking_carriers)
    assert [x.label for x in stored.required_actions] == ["New gloves", "Clean spreader"]
    assert len(alerts.open()) == 1


def test_tier0_resolves_by_reset_when_preconditions_are_met() -> None:
    alerts = AlertState(cfg())
    _apply(alerts, evaluate([assessment()], alerts, cfg()))
    [cmd] = evaluate(
        [assessment(RiskLevel.CLEAR, t=3000, reason="RESOLVED_BY_RESET")], alerts, cfg()
    )
    assert cmd.kind == "RESOLVE" and cmd.alert.state == AlertLifecycle.RESOLVED_BY_RESET
    assert not cmd.operator and cmd.cooldown_until is None
    alerts.apply(cmd)
    assert alerts.open() == [] and alerts.cooldowns() == {}
    assert alerts.all()[0].state == AlertLifecycle.RESOLVED_BY_RESET


def test_assertion_resolution_starts_a_cooldown_that_suppresses() -> None:
    alerts = AlertState(cfg(t_cooldown=120_000))
    _apply(alerts, evaluate([assessment()], alerts, cfg()))
    [cmd] = evaluate(
        [assessment(RiskLevel.CLEAR, t=3000, operator=True, reason="RESOLVED_BY_ASSERTION")],
        alerts,
        cfg(),
    )
    assert cmd.alert.state == AlertLifecycle.RESOLVED_BY_ASSERTION and cmd.operator
    assert cmd.cooldown_until == 123_000
    alerts.apply(cmd)
    key = cmd.alert.alert_key
    assert alerts.cooldowns() == {key: 123_000}
    [sup] = evaluate([assessment(t=50_000)], alerts, cfg())
    assert sup.kind == "SUPPRESS" and sup.cooldown_until == 123_000
    alerts.apply(sup)
    assert alerts.open() == [] and len(alerts.suppressions()) == 1
    [again] = evaluate([assessment(t=123_000)], alerts, cfg())
    assert again.kind == "RAISE"


def test_escalation_one_to_two_when_ticket_completes_with_pathway_open() -> None:
    alerts = AlertState(cfg())
    in_prep = assessment(
        RiskLevel.PATHWAY_OPEN, lifecycle=TicketLifecycle.IN_PREP, pathways=[DIRECT]
    )
    [raised] = evaluate([in_prep], alerts, cfg())
    assert raised.alert.tier == Tier.INTERRUPT
    assert raised.alert.headline == "STOP — gloves touched pesto"
    assert raised.alert.pathway_signature == pathway_signature("T48", "PINE_NUT", DIRECT)
    stored = alerts.apply(raised)
    complete = assessment(
        RiskLevel.PATHWAY_OPEN, lifecycle=TicketLifecycle.COMPLETE, pathways=[DIRECT], t=9000
    )
    [esc] = evaluate([complete], alerts, cfg())
    assert esc.kind == "ESCALATE" and esc.alert.tier == Tier.HOLD
    hold = alerts.apply(esc)
    assert hold.alert_id == stored.alert_id and hold.raised_at == stored.raised_at
    assert hold.state == AlertLifecycle.ESCALATED and hold.tier == Tier.HOLD
    assert hold.headline == "HOLD — TICKET T48 — DO NOT SEND"
    assert [x.kind for x in hold.required_actions] == ["HOLD", "REMAKE"]
    assert evaluate([complete], alerts, cfg()) == []


def test_tier1_resolves_on_pathway_resolved_with_the_assessed_reason() -> None:
    alerts = AlertState(cfg())
    _apply(
        alerts,
        evaluate(
            [
                assessment(
                    RiskLevel.PATHWAY_OPEN, lifecycle=TicketLifecycle.IN_PREP, pathways=[DIRECT]
                )
            ],
            alerts,
            cfg(),
        ),
    )
    resolved = assessment(
        RiskLevel.PATHWAY_RESOLVED,
        lifecycle=TicketLifecycle.IN_PREP,
        pathways=[pathway(["bin:pesto", "gloves", FOOD], broken=True)],
        operator=True,
        reason="RESOLVED_BY_ASSERTION",
        t=4000,
    )
    [cmd] = evaluate([resolved], alerts, cfg())
    assert cmd.kind == "RESOLVE" and cmd.alert.state == AlertLifecycle.RESOLVED_BY_ASSERTION


def test_tier2_never_auto_resolves() -> None:
    alerts = AlertState(cfg())
    complete = assessment(
        RiskLevel.PATHWAY_OPEN, lifecycle=TicketLifecycle.COMPLETE, pathways=[DIRECT]
    )
    _apply(alerts, evaluate([complete], alerts, cfg()))
    assert alerts.open()[0].tier == Tier.HOLD
    assert (
        evaluate(
            [assessment(RiskLevel.CLEAR, lifecycle=TicketLifecycle.COMPLETE, t=5000)], alerts, cfg()
        )
        == []
    )
    broken = [pathway(["bin:pesto", "gloves", FOOD], broken=True)]
    by_reset = assessment(
        RiskLevel.PATHWAY_RESOLVED,
        lifecycle=TicketLifecycle.COMPLETE,
        pathways=broken,
        reason="RESOLVED_BY_RESET",
        t=6000,
    )
    assert evaluate([by_reset], alerts, cfg()) == []
    vouched = by_reset.model_copy(
        update={"operator_resolution": True, "resolution_reason": "RESOLVED_BY_ASSERTION"}
    )
    [cmd] = evaluate([vouched], alerts, cfg())
    assert cmd.kind == "RESOLVE" and cmd.alert.state == AlertLifecycle.RESOLVED_BY_ASSERTION
    assert alerts.apply(cmd).state == AlertLifecycle.RESOLVED_BY_ASSERTION
    assert alerts.cooldowns() == {cmd.alert.alert_key: 6000 + cfg().t_cooldown}


def test_tier0_and_tier1_coexist_under_different_keys() -> None:
    a = assessment(
        RiskLevel.PATHWAY_OPEN,
        lifecycle=TicketLifecycle.IN_PREP,
        pathways=[DIRECT],
        blocking=["gloves"],
    )
    commands = evaluate([a], AlertState(cfg()), cfg())
    assert [c.kind for c in commands] == ["RAISE", "RAISE"]
    assert sorted(int(c.alert.tier) for c in commands) == [0, 1]
    assert len({c.alert.alert_key for c in commands}) == 2


def test_weak_evidence_downgrade_keeps_pathway_identity() -> None:
    weak = pathway(["bin:pesto", "spreader", FOOD], grade=EvidenceGrade.INFERRED)
    a = assessment(
        RiskLevel.PATHWAY_OPEN,
        lifecycle=TicketLifecycle.IN_PREP,
        grade=EvidenceGrade.INFERRED,
        pathways=[weak],
    )
    [cmd] = evaluate([a], AlertState(cfg()), cfg())
    assert cmd.alert.tier == Tier.RESET
    assert cmd.alert.pathway_signature == pathway_signature("T48", "PINE_NUT", weak)
    assert cmd.alert.headline == "PINE NUT — station not clean"
    assert [x.label for x in cmd.alert.required_actions] == ["Clean spreader"]
    assert cmd.alert.blocking_carriers == ["spreader"]


def test_multi_restriction_raises_and_resolves_with_the_condition() -> None:
    alerts = AlertState(cfg())
    multi = assessment(RiskLevel.UNVERIFIED, condition="MULTI_RESTRICTION", blocking=[])
    commands = evaluate([assessment(RiskLevel.CLEAR), multi], alerts, cfg())
    assert [c.kind for c in commands] == ["RAISE"]
    alert = commands[0].alert
    assert alert.headline == "Two active restrictions — sequence them"
    assert [x.kind for x in alert.required_actions] == ["SEQUENCE_TICKETS"]
    assert alert.pathway_signature == multi_restriction_signature("T48")
    _apply(alerts, commands)
    assert evaluate([assessment(RiskLevel.CLEAR), multi], alerts, cfg()) == []
    [cmd] = evaluate([assessment(RiskLevel.CLEAR, t=2000, operator=True)], alerts, cfg())
    assert cmd.kind == "RESOLVE" and cmd.alert.state == AlertLifecycle.RESOLVED_BY_RESET


def test_ticket_missing_from_assessments_is_left_to_observe() -> None:
    alerts = AlertState(cfg())
    _apply(alerts, evaluate([assessment()], alerts, cfg()))
    assert evaluate([assessment(RiskLevel.CLEAR, tid="T99")], alerts, cfg()) == []
    assert len(alerts.open()) == 1


def test_a_still_open_but_no_longer_best_pathway_alert_is_left_alone() -> None:
    alerts = AlertState(cfg())
    long = pathway(["bin:pesto", "gloves", "board", FOOD])
    _apply(
        alerts,
        evaluate(
            [
                assessment(
                    RiskLevel.PATHWAY_OPEN, lifecycle=TicketLifecycle.IN_PREP, pathways=[long]
                )
            ],
            alerts,
            cfg(),
        ),
    )
    both = assessment(
        RiskLevel.PATHWAY_OPEN, lifecycle=TicketLifecycle.IN_PREP, pathways=[DIRECT, long], t=2000
    )
    commands = evaluate([both], alerts, cfg())
    assert [c.kind for c in commands] == ["RAISE"]
    assert commands[0].alert.pathway_signature == pathway_signature("T48", "PINE_NUT", DIRECT)


def test_evaluate_is_deterministic_and_never_emits_two_commands_per_key() -> None:
    alerts = AlertState(cfg())
    inputs = [
        assessment(
            RiskLevel.PATHWAY_OPEN,
            lifecycle=TicketLifecycle.IN_PREP,
            pathways=[DIRECT],
            blocking=["gloves"],
        ),
        assessment(RiskLevel.UNVERIFIED, tid="T49", allergen="EGG", blocking=["bin:mayo"]),
        assessment(RiskLevel.UNVERIFIED, condition="MULTI_RESTRICTION", blocking=[]),
    ]
    a = evaluate(inputs, alerts, cfg())
    b = evaluate(inputs, alerts, cfg())
    assert [c.model_dump_json() for c in a] == [c.model_dump_json() for c in b]
    keys = [c.alert.alert_key for c in a]
    assert len(keys) == len(set(keys)) == 4
    assert [(c.alert.ticket_id, c.alert.allergen_id) for c in a] == sorted(
        (c.alert.ticket_id, c.alert.allergen_id) for c in a
    )
