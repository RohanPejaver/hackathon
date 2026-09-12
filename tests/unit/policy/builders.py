"""Hand-built RiskAssessment / Pathway / event fixtures for policy tests."""

from __future__ import annotations

from typing import Any

from src.domain import (
    EvidenceGrade,
    Mode,
    Pathway,
    RiskAssessment,
    RiskLevel,
    TicketLifecycle,
)
from src.events.catalog import (
    GradedAlertAcknowledged,
    GradedAlertUpdated,
    GradedContactBegin,
    GradedTicketReleased,
    GradedTicketVoided,
)

STATION = "demo-bagel"


def pathway(
    nodes: list[str],
    grade: EvidenceGrade = EvidenceGrade.OBSERVED,
    broken: bool = False,
    event_ids: list[str] | None = None,
    allergen: str = "PINE_NUT",
) -> Pathway:
    ids = event_ids or [f"e{i + 1}" for i in range(len(nodes) - 1)]
    return Pathway(
        allergen_id=allergen,
        nodes=nodes,
        event_ids=ids,
        grade=grade,
        hops=len(ids) - 1,
        broken=broken,
    )


def assessment(
    level: RiskLevel = RiskLevel.UNVERIFIED,
    *,
    lifecycle: TicketLifecycle = TicketLifecycle.BOUND,
    grade: EvidenceGrade = EvidenceGrade.OBSERVED,
    pathways: list[Pathway] = (),  # type: ignore[assignment]
    blocking: list[str] = (),  # type: ignore[assignment]
    tid: str = "T48",
    allergen: str = "PINE_NUT",
    t: int = 1000,
    mode: Mode = Mode.FULL,
    condition: str | None = None,
    operator: bool = False,
    reason: Any = None,
    cause: str = "e-cause",
) -> RiskAssessment:
    if level == RiskLevel.UNVERIFIED and not blocking and condition is None:
        blocking = ["gloves"]
    return RiskAssessment(
        ticket_id=tid,
        allergen_id=allergen,
        level=level,
        pathways=list(pathways),
        blocking_carriers=list(blocking),
        max_grade=grade,
        assessed_at=t,
        config_version="1",
        knowledge_version="1",
        ticket_lifecycle=lifecycle,
        station_id=STATION,
        mode=mode,
        cause_event_id=cause,
        cause_event_type="CONTACT_BEGIN",
        operator_resolution=operator,
        resolution_reason=reason,
        condition=condition,
    )


def _envelope(eid: str, t: int, source: str = "OPERATOR") -> dict[str, Any]:
    return dict(
        event_id=eid,
        t_occurred=t,
        station_id=STATION,
        source=source,
        grade=EvidenceGrade.OBSERVED,
        seq=t,
        t_committed=t,
    )


def ack(alert_id: str, t: int, slot: int = 0) -> GradedAlertAcknowledged:
    return GradedAlertAcknowledged(
        **_envelope(f"ack-{t}", t), alert_id=alert_id, pathway_signature="sig", worker_slot=slot
    )


def dismiss(alert_id: str, t: int, slot: int | None = 0) -> GradedAlertUpdated:
    return GradedAlertUpdated(
        **_envelope(f"dis-{t}", t), alert_id=alert_id, pathway_signature="sig", worker_slot=slot
    )


def voided(tid: str, t: int) -> GradedTicketVoided:
    return GradedTicketVoided(**_envelope(f"void-{t}", t), ticket=tid, reason="remake")


def released(tid: str, t: int) -> GradedTicketReleased:
    return GradedTicketReleased(**_envelope(f"rel-{t}", t), ticket=tid, worker_slot=0)


def contact(t: int) -> GradedContactBegin:
    return GradedContactBegin(
        **_envelope(f"c-{t}", t, "PERCEPTION"),
        a="gloves",
        b="board",
        contact_point={"x": 0, "y": 0},
    )
