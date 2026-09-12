"""Alert construction: headline, required actions and the evidence trace (16, 25, 26).

The derivation is built from the same Pathway/RiskAssessment that drove the decision, so
the explanation cannot drift from the behaviour.

CONTRACT-GAP: `evaluate(assessments, alerts, cfg)` carries no WorldState, but carrier kinds
(for required_actions), per-edge timestamps/grades and Tier 0 taint provenance live only
there. `state` is therefore an optional input; without it kinds are inferred from carrier
ids and edge times fall back to the assessment time.
"""

from __future__ import annotations

from pydantic import JsonValue

from src.domain import (
    Action,
    Alert,
    AlertLifecycle,
    CarrierKind,
    Config,
    EpistemicStatus,
    EvidenceGrade,
    Pathway,
    ResetKind,
    RiskAssessment,
    StateDelta,
    TaintRecord,
    Tier,
    TraceStep,
    WorldState,
    effective_epistemic,
)
from src.knowledge import UNKNOWN_ALLERGEN_PROFILE

from . import copy as text
from .identity import (
    alert_key,
    multi_restriction_signature,
    pathway_signature,
    precondition_signature,
)

RULE_ZONE_ACQUIRE = "zone_acquire"
RULE_CONTACT_TRANSFER = "contact_transfer"
RULE_ABSENCE = "absence"
RULE_UNVERIFIED = "unverified"
RULE_PRECONDITION_UNMET = "precondition_unmet"
RULE_CONDITION = "condition"
RULE_PATHWAY_OPEN = "pathway_open"
RULE_ALERT = "alert"

_RESET_KIND: dict[CarrierKind, ResetKind] = {
    CarrierKind.GLOVES: ResetKind.GLOVE_CHANGE,
    CarrierKind.TOOL: ResetKind.TOOL_SWAP,
    CarrierKind.SURFACE: ResetKind.SURFACE_SWAP,
    CarrierKind.CONTAINER: ResetKind.OPERATOR_ASSERTION,
}


def carrier_kind(carrier_id: str, state: WorldState | None) -> CarrierKind:
    if state is not None and carrier_id in state.station.carriers:
        return state.station.carriers[carrier_id].kind
    lower = carrier_id.lower()
    if lower.startswith("food:"):
        return CarrierKind.FOOD
    if "glove" in lower:
        return CarrierKind.GLOVES
    if lower.startswith(text.CONTAINER_PREFIX) or "tub" in lower or "container" in lower:
        return CarrierKind.CONTAINER
    if "board" in lower or "landing" in lower or "surface" in lower:
        return CarrierKind.SURFACE
    return CarrierKind.TOOL


def source_name(root: str, state: WorldState | None) -> str:
    """What the worker calls the root source: the ingredient zone's contents ("pesto")."""
    if state is not None:
        for zone in state.station.zones.values():
            if zone.bound_carrier == root and zone.contents:
                return ", ".join(zone.contents)
    return root.removeprefix(text.CONTAINER_PREFIX)


def _edge(
    event_id: str, state: WorldState | None, default_t: int, default_grade: EvidenceGrade
) -> tuple[int, EvidenceGrade]:
    if state is not None:
        for e in state.contacts:
            if e.event_id == event_id:
                return e.t_occurred, e.grade
    return default_t, default_grade


def reset_action(carrier_id: str, kind: CarrierKind) -> Action:
    if kind == CarrierKind.GLOVES:
        return Action(kind="NEW_GLOVES", carrier_id=carrier_id, label=text.LABEL_NEW_GLOVES)
    if kind == CarrierKind.SURFACE:
        return Action(
            kind="SWAP_SURFACE",
            carrier_id=carrier_id,
            label=text.LABEL_FRESH_SURFACE.format(carrier=carrier_id),
        )
    if kind == CarrierKind.CONTAINER:
        return Action(
            kind="USE_SEALED_BACKUP",
            carrier_id=carrier_id,
            label=text.LABEL_SEALED_BACKUP.format(container=text.container_display(carrier_id)),
        )
    if kind == CarrierKind.FOOD:
        return Action(kind="VERIFY", carrier_id=carrier_id, label=text.LABEL_CONFIRM)
    return Action(
        kind="SWAP_TOOL",
        carrier_id=carrier_id,
        label=text.LABEL_CLEAN_TOOL.format(carrier=carrier_id),
    )


def interrupt_action(carrier_id: str, kind: CarrierKind) -> Action:
    if kind == CarrierKind.TOOL:
        return Action(kind="SWAP_TOOL", carrier_id=carrier_id, label=text.LABEL_SWAP_TOOL)
    if kind == CarrierKind.FOOD:
        return Action(kind="REMAKE", carrier_id=None, label=text.LABEL_REMAKE)
    return reset_action(carrier_id, kind)


def _step(
    event_id: str,
    t: int,
    rule_id: str,
    carrier_id: str | None,
    field: str,
    after: JsonValue,
    grade: EvidenceGrade,
    narrative: str,
) -> TraceStep:
    return TraceStep(
        event_id=event_id,
        t_occurred=t,
        rule_id=rule_id,
        state_delta=StateDelta(
            event_id=event_id, rule_id=rule_id, carrier_id=carrier_id, field=field, after=after
        ),
        grade=grade,
        narrative=narrative,
    )


def _absence_step(carrier_id: str, kind: CarrierKind, event_id: str, t: int) -> TraceStep | None:
    reset_kind = _RESET_KIND.get(kind)
    if reset_kind is None:
        return None
    return _step(
        event_id,
        t,
        RULE_ABSENCE,
        carrier_id,
        "reset",
        None,
        EvidenceGrade.PESSIMISTIC,
        text.NARRATIVE_ABSENCE.format(reset_kind=reset_kind.value, carrier=carrier_id),
    )


def _alert_step(a: RiskAssessment, tier: Tier, headline: str) -> TraceStep:
    after: JsonValue = {"tier": int(tier), "headline": headline}
    return _step(
        a.cause_event_id,
        a.assessed_at,
        RULE_ALERT,
        None,
        "alert",
        after,
        a.max_grade,
        text.NARRATIVE_ALERT.format(tier=int(tier), headline=headline),
    )


def pathway_steps(a: RiskAssessment, p: Pathway, state: WorldState | None) -> list[TraceStep]:
    steps: list[TraceStep] = []
    for i, event_id in enumerate(p.event_ids):
        t, grade = _edge(event_id, state, a.assessed_at, p.grade)
        if i == 0:
            after: JsonValue = {p.allergen_id: {"source": p.nodes[0]}}
            steps.append(
                _step(
                    event_id,
                    t,
                    RULE_ZONE_ACQUIRE,
                    p.nodes[1],
                    "taints",
                    after,
                    grade,
                    text.NARRATIVE_ZONE_ACQUIRE.format(carrier=p.nodes[1], zone=p.nodes[0]),
                )
            )
        else:
            hop: JsonValue = {p.allergen_id: {"hop": i}}
            steps.append(
                _step(
                    event_id,
                    t,
                    RULE_CONTACT_TRANSFER,
                    p.nodes[i + 1],
                    "taints",
                    hop,
                    grade,
                    text.NARRATIVE_CONTACT_TRANSFER.format(a=p.nodes[i], b=p.nodes[i + 1]),
                )
            )
    last = p.event_ids[-1] if p.event_ids else a.cause_event_id
    for node in p.nodes[1:-1]:
        absence = _absence_step(node, carrier_kind(node, state), last, a.assessed_at)
        if absence is not None:
            steps.append(absence)
    path: JsonValue = list(p.nodes)
    steps.append(
        _step(
            last,
            a.assessed_at,
            RULE_PATHWAY_OPEN,
            p.nodes[-1],
            "pathway",
            path,
            p.grade,
            text.NARRATIVE_PATHWAY_OPEN.format(path=" -> ".join(p.nodes), hops=p.hops),
        )
    )
    return steps


def _taint_steps(carrier_id: str, taint: TaintRecord) -> TraceStep:
    if taint.hops == 0:
        after: JsonValue = {taint.allergen_id: {"source": taint.source_carrier_id}}
        return _step(
            taint.source_event_id,
            taint.acquired_at,
            RULE_ZONE_ACQUIRE,
            carrier_id,
            "taints",
            after,
            taint.grade,
            text.NARRATIVE_ZONE_ACQUIRE.format(carrier=carrier_id, zone=taint.source_carrier_id),
        )
    hop: JsonValue = {taint.allergen_id: {"hop": taint.hops}}
    return _step(
        taint.source_event_id,
        taint.acquired_at,
        RULE_CONTACT_TRANSFER,
        carrier_id,
        "taints",
        hop,
        taint.grade,
        text.NARRATIVE_CONTACT_TRANSFER.format(a=taint.source_carrier_id, b=carrier_id),
    )


def precondition_steps(
    a: RiskAssessment, blocking: list[str], state: WorldState | None, cfg: Config
) -> list[TraceStep]:
    steps: list[TraceStep] = []
    if state is not None:
        for cid in blocking:
            carrier = state.station.carriers.get(cid)
            if carrier is None:
                continue
            taints = sorted(
                (
                    t
                    for t in carrier.taints.values()
                    if t.allergen_id in (a.allergen_id, UNKNOWN_ALLERGEN_PROFILE)
                ),
                key=lambda t: (t.acquired_at, t.source_event_id),
            )
            for taint in taints:
                steps.append(_taint_steps(cid, taint))
            if taints:
                absence = _absence_step(
                    cid, carrier.kind, taints[-1].source_event_id, a.assessed_at
                )
                if absence is not None:
                    steps.append(absence)
                continue
            status = effective_epistemic(carrier, state.t_occurred, cfg)
            if status != EpistemicStatus.TRACKED:
                if carrier.last_observed_at is None:
                    narrative = text.NARRATIVE_NEVER_OBSERVED.format(
                        carrier=cid, status=status.value
                    )
                else:
                    narrative = text.NARRATIVE_UNVERIFIED.format(
                        carrier=cid,
                        status=status.value,
                        duration=text.duration(state.t_occurred - carrier.last_observed_at),
                    )
                steps.append(
                    _step(
                        a.cause_event_id,
                        a.assessed_at,
                        RULE_UNVERIFIED,
                        cid,
                        "epistemic",
                        status.value,
                        EvidenceGrade.PESSIMISTIC,
                        narrative,
                    )
                )
    blocked: JsonValue = list(blocking)
    steps.append(
        _step(
            a.cause_event_id,
            a.assessed_at,
            RULE_PRECONDITION_UNMET,
            None,
            "blocking",
            blocked,
            a.max_grade,
            text.NARRATIVE_PRECONDITION_UNMET.format(blocking=", ".join(blocking)),
        )
    )
    return steps


def _alert(
    a: RiskAssessment,
    signature: str,
    tier: Tier,
    headline: str,
    actions: list[Action],
    derivation: list[TraceStep],
    blocking: list[str],
    body: str | None,
) -> Alert:
    return Alert(
        alert_id="pending",
        alert_key=alert_key(a.station_id, signature),
        pathway_signature=signature,
        tier=tier,
        ticket_id=a.ticket_id,
        allergen_id=a.allergen_id,
        headline=headline,
        required_actions=actions,
        derivation=[*derivation, _alert_step(a, tier, headline)],
        raised_at=a.assessed_at,
        state=AlertLifecycle.RAISED,
        acknowledged_by_slot=None,
        blocking_carriers=blocking,
        updated_at=a.assessed_at,
        body=body,
        dismissed_until=None,
    )


def build_precondition_alert(a: RiskAssessment, state: WorldState | None, cfg: Config) -> Alert:
    blocking = list(a.blocking_carriers)
    actions = [reset_action(c, carrier_kind(c, state)) for c in blocking]
    return _alert(
        a,
        precondition_signature(a.ticket_id, a.allergen_id),
        Tier.RESET,
        text.tier0_headline(a.allergen_id),
        actions,
        precondition_steps(a, blocking, state, cfg),
        blocking,
        None,
    )


def build_multi_alert(a: RiskAssessment) -> Alert:
    condition: JsonValue = a.condition
    step = _step(
        a.cause_event_id,
        a.assessed_at,
        RULE_CONDITION,
        None,
        "conditions",
        condition,
        a.max_grade,
        text.NARRATIVE_CONDITION.format(condition=a.condition),
    )
    return _alert(
        a,
        multi_restriction_signature(a.ticket_id),
        Tier.RESET,
        text.MULTI_HEADLINE,
        [Action(kind="SEQUENCE_TICKETS", carrier_id=None, label=text.LABEL_SEQUENCE_TICKETS)],
        [step],
        [],
        None,
    )


def build_pathway_alert(
    a: RiskAssessment, tier: Tier, p: Pathway, state: WorldState | None
) -> Alert:
    root = p.nodes[0]
    implicated = p.nodes[1] if len(p.nodes) > 2 else p.nodes[-1]
    intermediates = list(p.nodes[1:-1])
    source = source_name(root, state)
    kind = carrier_kind(implicated, state)
    headline: str
    body: str | None
    actions: list[Action]
    if tier == Tier.HOLD:
        t_source, _ = _edge(p.event_ids[0], state, a.assessed_at, p.grade)
        headline = text.tier2_headline(a.ticket_id)
        body = text.tier2_body(a.allergen_id, implicated, source, t_source)
        actions = [
            Action(kind="HOLD", carrier_id=implicated, label=text.LABEL_CONFIRM),
            Action(kind="REMAKE", carrier_id=None, label=text.LABEL_REMAKE),
        ]
    elif tier == Tier.INTERRUPT:
        headline = text.tier1_headline(implicated, source)
        body = text.tier1_body(implicated, source)
        actions = [interrupt_action(implicated, kind)]
    else:
        # Weak evidence downgrades to the cheapest tier (ADR-0005): a reset checklist.
        headline = text.tier0_headline(a.allergen_id)
        body = None
        actions = [reset_action(c, carrier_kind(c, state)) for c in intermediates] or [
            reset_action(implicated, kind)
        ]
    return _alert(
        a,
        pathway_signature(a.ticket_id, a.allergen_id, p),
        tier,
        headline,
        actions,
        pathway_steps(a, p, state),
        intermediates,
        body,
    )
