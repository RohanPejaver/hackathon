"""InterventionPolicy.evaluate — tier selection, alert_key dedup, cooldown, escalation
(15 §Tier selection, 16, ADR-0005, ADR-0011). Pure."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import (
    GRADE_RANK,
    Alert,
    AlertCommand,
    AlertLifecycle,
    Config,
    EvidenceGrade,
    Mode,
    Pathway,
    RiskAssessment,
    RiskLevel,
    TicketLifecycle,
    Tier,
    WorldState,
)

from .build import build_multi_alert, build_pathway_alert, build_precondition_alert
from .identity import MULTI_RESTRICTION, multi_restriction_signature, pathway_signature
from .state import AlertState

_ASSERTION = "RESOLVED_BY_ASSERTION"
_RESET = "RESOLVED_BY_RESET"


@dataclass(frozen=True)
class _Want:
    tier: Tier
    alert: Alert
    assessment: RiskAssessment


def pathway_tier(a: RiskAssessment) -> Tier:
    """15 §Tier selection + ADR-0005 (weak evidence downgrades) + ADR-0011 (no Tier 1 in
    PROTOCOL_ONLY). Tier 1 -> 2 is lifecycle-driven: the ticket reaches COMPLETE/HELD with
    the pathway still open; no timer."""
    weak = GRADE_RANK[a.max_grade] < GRADE_RANK[EvidenceGrade.OBSERVED]
    if weak or a.ticket_lifecycle == TicketLifecycle.BOUND:
        return Tier.RESET
    if a.ticket_lifecycle == TicketLifecycle.IN_PREP:
        return Tier.RESET if a.mode == Mode.PROTOCOL_ONLY else Tier.INTERRUPT
    return Tier.HOLD


def _open_pathways(a: RiskAssessment) -> list[Pathway]:
    return [p for p in a.pathways if not p.broken]


def _best(open_: list[Pathway]) -> Pathway:
    return max(open_, key=lambda p: (GRADE_RANK[p.grade], -p.hops))


def _wants(a: RiskAssessment, state: WorldState | None, cfg: Config) -> list[_Want]:
    if a.condition == MULTI_RESTRICTION:
        return [_Want(Tier.RESET, build_multi_alert(a), a)]
    wants: list[_Want] = []
    if a.blocking_carriers:
        wants.append(_Want(Tier.RESET, build_precondition_alert(a, state, cfg), a))
    open_ = _open_pathways(a) if a.level == RiskLevel.PATHWAY_OPEN else []
    if open_:
        tier = pathway_tier(a)
        wants.append(_Want(tier, build_pathway_alert(a, tier, _best(open_), state), a))
    return wants


def _fingerprint(alert: Alert) -> tuple[object, ...]:
    return (
        alert.headline,
        alert.body,
        tuple(alert.blocking_carriers),
        tuple((x.kind, x.carrier_id, x.label) for x in alert.required_actions),
        tuple((s.rule_id, s.event_id, s.narrative) for s in alert.derivation),
    )


def _carry(existing: Alert, new: Alert, state: AlertLifecycle, tier: Tier) -> Alert:
    return new.model_copy(
        update={
            "alert_id": existing.alert_id,
            "raised_at": existing.raised_at,
            "state": state,
            "tier": tier,
            "acknowledged_by_slot": existing.acknowledged_by_slot,
            "dismissed_until": existing.dismissed_until,
        }
    )


def _resolve(existing: Alert, reason: str, a: RiskAssessment, cfg: Config) -> AlertCommand:
    assertion = reason == _ASSERTION
    return AlertCommand(
        kind="RESOLVE",
        alert=existing.model_copy(
            update={"state": AlertLifecycle(reason), "updated_at": a.assessed_at}
        ),
        t_occurred=a.assessed_at,
        cause_event_id=a.cause_event_id,
        operator=assertion,
        cooldown_until=a.assessed_at + cfg.t_cooldown if assertion else None,
    )


def _resolution(existing: Alert, a: RiskAssessment, cfg: Config) -> AlertCommand | None:
    """Rules for an open alert nothing wants any more (16 §Lifecycle)."""
    if existing.pathway_signature == multi_restriction_signature(existing.ticket_id):
        return _resolve(existing, _RESET, a, cfg)
    if existing.tier == Tier.HOLD:
        # Tier 2 never auto-resolves: only a human vouching clears a hold.
        return _resolve(existing, _ASSERTION, a, cfg) if a.operator_resolution else None
    if existing.tier == Tier.INTERRUPT:
        return _resolve(existing, a.resolution_reason or _RESET, a, cfg)
    return _resolve(existing, _ASSERTION if a.operator_resolution else _RESET, a, cfg)


def _matching(existing: Alert, assessments: list[RiskAssessment]) -> RiskAssessment | None:
    same_ticket = [x for x in assessments if x.ticket_id == existing.ticket_id]
    for x in same_ticket:
        if x.allergen_id == existing.allergen_id and x.condition is None:
            return x
    return same_ticket[0] if same_ticket else None


def _still_open(existing: Alert, a: RiskAssessment) -> bool:
    """A pathway alert whose pathway is still open but no longer the best stays as it is."""
    if a.condition is not None or existing.allergen_id != a.allergen_id:
        return False
    return any(
        pathway_signature(a.ticket_id, a.allergen_id, p) == existing.pathway_signature
        for p in _open_pathways(a)
    )


def evaluate(
    assessments: list[RiskAssessment],
    alerts: AlertState,
    cfg: Config,
    state: WorldState | None = None,
) -> list[AlertCommand]:
    wants: dict[str, _Want] = {}
    for a in assessments:
        for w in _wants(a, state, cfg):
            wants.setdefault(w.alert.alert_key, w)
    assessed = {a.ticket_id for a in assessments}
    cooldowns = alerts.cooldowns()
    commands: list[AlertCommand] = []
    handled: set[str] = set()

    for existing in alerts.open():
        key = existing.alert_key
        if key in handled:
            continue
        handled.add(key)
        want = wants.get(key)
        if want is not None:
            a = want.assessment
            if want.tier > existing.tier:
                commands.append(
                    AlertCommand(
                        kind="ESCALATE",
                        alert=_carry(existing, want.alert, AlertLifecycle.ESCALATED, want.tier),
                        t_occurred=a.assessed_at,
                        cause_event_id=a.cause_event_id,
                    )
                )
            elif want.tier == existing.tier and _fingerprint(want.alert) != _fingerprint(existing):
                commands.append(
                    AlertCommand(
                        kind="UPDATE",
                        alert=_carry(existing, want.alert, existing.state, existing.tier),
                        t_occurred=a.assessed_at,
                        cause_event_id=a.cause_event_id,
                    )
                )
            continue
        if existing.ticket_id not in assessed:
            continue  # voided / released tickets are folded by AlertState.observe
        a_match = _matching(existing, assessments)
        if a_match is None or _still_open(existing, a_match):
            continue
        cmd = _resolution(existing, a_match, cfg)
        if cmd is not None:
            commands.append(cmd)

    for key, want in wants.items():
        if key in handled:
            continue
        a = want.assessment
        until = cooldowns.get(key)
        if until is not None and a.assessed_at < until:
            commands.append(
                AlertCommand(
                    kind="SUPPRESS",
                    alert=want.alert,
                    t_occurred=a.assessed_at,
                    cause_event_id=a.cause_event_id,
                    cooldown_until=until,
                )
            )
        else:
            commands.append(
                AlertCommand(
                    kind="RAISE",
                    alert=want.alert,
                    t_occurred=a.assessed_at,
                    cause_event_id=a.cause_event_id,
                )
            )
    commands.sort(key=lambda c: (c.alert.ticket_id, c.alert.allergen_id, c.kind, c.alert.alert_key))
    return commands
