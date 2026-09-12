"""AlertState.observe folds operator/ticket events from the log (26 §Worker actions)."""

from src.domain import AlertLifecycle, RiskLevel, TicketLifecycle, Tier
from src.policy import AlertState, evaluate
from tests.unit.policy.builders import ack, assessment, contact, dismiss, pathway, released, voided
from tests.unit.risk.builders import cfg

FOOD = "food:T48"


def _raised(alerts: AlertState, *assessments):
    return [alerts.apply(c) for c in evaluate(list(assessments), alerts, cfg())]


def test_acknowledge_from_raised_and_escalated_only_and_idempotent() -> None:
    alerts = AlertState(cfg())
    [alert] = _raised(alerts, assessment())
    alerts.observe(ack(alert.alert_id, 2000, slot=1))
    got = alerts.by_key(alert.alert_key)
    assert got is not None and got.state == AlertLifecycle.ACKNOWLEDGED
    assert got.acknowledged_by_slot == 1 and got.updated_at == 2000
    alerts.observe(ack(alert.alert_id, 2000, slot=1))
    alerts.observe(ack(alert.alert_id, 3000, slot=0))
    again = alerts.by_key(alert.alert_key)
    assert again is not None and again.acknowledged_by_slot == 1 and again.updated_at == 2000
    alerts.observe(ack("al-404", 4000))
    assert len(alerts.open()) == 1


def test_dismissal_sets_dismissed_until_only_and_never_for_tier2() -> None:
    alerts = AlertState(cfg(t_cooldown=120_000))
    [t0] = _raised(alerts, assessment())
    alerts.observe(dismiss(t0.alert_id, 5000))
    got = alerts.all()[0]
    assert got.state == AlertLifecycle.RAISED and got.dismissed_until == 125_000
    alerts.observe(dismiss(t0.alert_id, 6000, slot=None))  # not a worker action
    assert alerts.all()[0].dismissed_until == 125_000
    complete = assessment(
        RiskLevel.PATHWAY_OPEN,
        lifecycle=TicketLifecycle.COMPLETE,
        pathways=[pathway(["bin:pesto", "gloves", FOOD])],
        tid="T50",
    )
    [t2] = _raised(alerts, complete)
    assert t2.tier == Tier.HOLD
    alerts.observe(dismiss(t2.alert_id, 7000))
    assert alerts.by_key(t2.alert_key).dismissed_until is None  # type: ignore[union-attr]


def test_ticket_voided_expires_tier0_and_remakes_tier1() -> None:
    alerts = AlertState(cfg())
    in_prep = assessment(
        RiskLevel.PATHWAY_OPEN,
        lifecycle=TicketLifecycle.IN_PREP,
        pathways=[pathway(["bin:pesto", "gloves", FOOD])],
        blocking=["gloves"],
    )
    _raised(alerts, in_prep, assessment(tid="T49"))
    assert len(alerts.open()) == 3
    alerts.observe(voided("T48", 9000))
    alerts.observe(voided("T48", 9000))
    states = {(a.ticket_id, int(a.tier)): a.state for a in alerts.all()}
    assert states[("T48", 0)] == AlertLifecycle.EXPIRED
    assert states[("T48", 1)] == AlertLifecycle.RESOLVED_BY_REMAKE
    assert states[("T49", 0)] == AlertLifecycle.RAISED
    assert [a.ticket_id for a in alerts.open()] == ["T49"]


def test_ticket_released_resolves_tier2_by_assertion_with_cooldown() -> None:
    alerts = AlertState(cfg(t_cooldown=120_000))
    complete = assessment(
        RiskLevel.PATHWAY_OPEN,
        lifecycle=TicketLifecycle.COMPLETE,
        pathways=[pathway(["bin:pesto", "gloves", FOOD])],
        blocking=["gloves"],
    )
    _raised(alerts, complete)
    alerts.observe(released("T48", 30_000))
    by_tier = {int(a.tier): a for a in alerts.all()}
    assert by_tier[2].state == AlertLifecycle.RESOLVED_BY_ASSERTION
    assert by_tier[0].state == AlertLifecycle.RAISED
    assert alerts.cooldowns() == {by_tier[2].alert_key: 150_000}


def test_observe_ignores_unrelated_events() -> None:
    alerts = AlertState(cfg())
    [alert] = _raised(alerts, assessment())
    alerts.observe(contact(5000))
    assert alerts.all() == [alert]


def test_open_ordering_all_and_by_key() -> None:
    alerts = AlertState(cfg())
    _raised(alerts, assessment(tid="T2", t=5000))
    _raised(alerts, assessment(tid="T1", t=5000))
    _raised(alerts, assessment(tid="T0", t=4000))
    # (raised_at, raise order): T0 is earliest; T2 and T1 tie on time and keep raise order
    assert [a.ticket_id for a in alerts.open()] == ["T0", "T2", "T1"]
    assert [a.alert_id for a in alerts.open()] == ["al-3", "al-1", "al-2"]
    [cmd] = evaluate([assessment(RiskLevel.CLEAR, tid="T0", t=6000)], alerts, cfg())
    alerts.apply(cmd)
    assert alerts.by_key(cmd.alert.alert_key) is None
    assert len(alerts.all()) == 3 and len(alerts.open()) == 2


def test_apply_resolve_for_unknown_alert_stores_nothing() -> None:
    alerts = AlertState(cfg())
    [cmd] = evaluate([assessment()], alerts, cfg())
    resolve = cmd.model_copy(
        update={
            "kind": "RESOLVE",
            "alert": cmd.alert.model_copy(update={"state": AlertLifecycle.RESOLVED_BY_RESET}),
        }
    )
    assert alerts.apply(resolve) == resolve.alert
    assert alerts.all() == []
