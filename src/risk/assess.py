"""assess : (WorldState, List<Ticket>, Knowledge, Config) -> List<RiskAssessment> (15)."""

from __future__ import annotations

from typing import Literal

from src.domain import (
    GRADE_RANK,
    Config,
    EvidenceGrade,
    Knowledge,
    Pathway,
    Resolution,
    RiskAssessment,
    RiskLevel,
    Ticket,
    TicketLifecycle,
    WorldState,
)
from src.knowledge import KnowledgeProvider

from .pathways import breaking_resets, find_pathways
from .preconditions import blocking_carriers, matching_taints, required_carriers

MULTI_RESTRICTION = "MULTI_RESTRICTION"
_ACTIVE = frozenset(
    {
        TicketLifecycle.BOUND,
        TicketLifecycle.IN_PREP,
        TicketLifecycle.COMPLETE,
        TicketLifecycle.HELD,
    }
)
_SEARCHABLE = frozenset({TicketLifecycle.IN_PREP, TicketLifecycle.COMPLETE, TicketLifecycle.HELD})
_Reason = Literal["RESOLVED_BY_RESET", "RESOLVED_BY_ASSERTION", "RESOLVED_BY_REMAKE"]


def _max_grade(grades: list[EvidenceGrade]) -> EvidenceGrade:
    return max(grades, key=lambda g: GRADE_RANK[g])


def _reason(operator: bool) -> _Reason:
    return "RESOLVED_BY_ASSERTION" if operator else "RESOLVED_BY_RESET"


def _restricted_ids(ticket: Ticket) -> list[str]:
    return sorted(
        {
            a
            for r in ticket.restrictions
            if r.resolution == Resolution.RESOLVED
            for a in r.allergen_ids
        }
    )


def _assess_allergen(
    state: WorldState,
    ticket: Ticket,
    allergen_id: str,
    allergens: frozenset[str],
    required: list[str],
    cfg: Config,
) -> RiskAssessment:
    food = f"food:{ticket.ticket_id}"
    pathways: list[Pathway] = []
    if ticket.lifecycle in _SEARCHABLE and food in state.station.carriers:
        pathways = find_pathways(state, food, allergens, cfg)
    open_ = [p for p in pathways if not p.broken]
    broken = [p for p in pathways if p.broken]
    blocking = blocking_carriers(state, required, allergens, cfg, ticket.bound_at)
    breaking = [r for p in broken for r in breaking_resets(state, p)]
    operator = any(r.operator for r in breaking)

    level: RiskLevel
    max_grade: EvidenceGrade
    operator_resolution = False
    reason: _Reason | None = None
    if open_:
        level = RiskLevel.PATHWAY_OPEN
        max_grade = _max_grade([p.grade for p in open_])
        operator_resolution = operator
        reason = _reason(operator) if broken else None
        pathways = [*open_, *broken]
    elif pathways:
        level = RiskLevel.PATHWAY_RESOLVED
        max_grade = _max_grade([p.grade for p in pathways])
        operator_resolution = operator
        reason = _reason(operator)
    elif blocking:
        level = RiskLevel.UNVERIFIED
        carriers = state.station.carriers
        taint_grades = [
            carriers[c].taints[a].grade
            for c in blocking
            for a in matching_taints(carriers[c], allergens)
            if a in carriers[c].taints
        ]
        max_grade = _max_grade(taint_grades) if taint_grades else EvidenceGrade.PESSIMISTIC
    else:
        # CLEAR: "no pathway found under current evidence" — never a claim about the food.
        level = RiskLevel.CLEAR
        max_grade = EvidenceGrade.OBSERVED
        resets = sorted(
            (r for r in state.resets if r.carrier_id in required),
            key=lambda r: (r.t_occurred, r.event_id),
        )
        if resets:
            operator_resolution = resets[-1].operator
            reason = _reason(operator_resolution)

    return RiskAssessment(
        ticket_id=ticket.ticket_id,
        allergen_id=allergen_id,
        level=level,
        pathways=pathways,
        blocking_carriers=blocking,
        max_grade=max_grade,
        assessed_at=state.t_occurred,
        config_version=cfg.config_version,
        knowledge_version=cfg.knowledge_version,
        ticket_lifecycle=ticket.lifecycle,
        station_id=state.station.station_id,
        mode=state.station.mode,
        cause_event_id=state.last_event_id,
        cause_event_type=state.last_event_type,
        operator_resolution=operator_resolution,
        resolution_reason=reason,
    )


def _multi(state: WorldState, ticket: Ticket, allergen_id: str, cfg: Config) -> RiskAssessment:
    return RiskAssessment(
        ticket_id=ticket.ticket_id,
        allergen_id=allergen_id,
        level=RiskLevel.UNVERIFIED,
        max_grade=EvidenceGrade.OBSERVED,
        assessed_at=state.t_occurred,
        config_version=cfg.config_version,
        knowledge_version=cfg.knowledge_version,
        ticket_lifecycle=ticket.lifecycle,
        station_id=state.station.station_id,
        mode=state.station.mode,
        cause_event_id=state.last_event_id,
        cause_event_type=state.last_event_type,
        condition=MULTI_RESTRICTION,
    )


def assess(
    state: WorldState, tickets: list[Ticket], k: Knowledge, cfg: Config
) -> list[RiskAssessment]:
    """One assessment per (active restricted ticket, restricted allergen), in ticket order,
    plus one MULTI_RESTRICTION assessment per such ticket while the station condition holds
    (17 §Concurrency). Preconditions are evaluated for every level so a Tier 0 checklist can
    stay up beside an open pathway."""
    kp = KnowledgeProvider(k)
    multi = MULTI_RESTRICTION in state.conditions
    out: list[RiskAssessment] = []
    for ticket in tickets:
        if ticket.lifecycle not in _ACTIVE:
            continue
        restricted = _restricted_ids(ticket)
        if not restricted:
            continue
        required = required_carriers(state, ticket, kp)
        for a in restricted:
            out.append(_assess_allergen(state, ticket, a, kp.closure(a), required, cfg))
        if multi:
            out.append(_multi(state, ticket, restricted[0], cfg))
    return out
