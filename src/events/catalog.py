"""Event catalog (12), including human-approved Q4 gap extensions."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from src.domain import (
    AlertCommand,
    EpistemicStatus,
    EvidenceGrade,
    Mode,
    Model,
    Point2D,
    Restriction,
)


class EvidenceRef(Model):
    track_ids: list[str] = Field(default_factory=list)
    zone_ids: list[str] = Field(default_factory=list)
    frame_range: tuple[int, int] | None = None


class SemanticEnvelope(Model):
    event_id: str
    t_occurred: int
    station_id: str
    schema_version: Literal[1] = 1
    source: Literal["PERCEPTION", "OPERATOR", "ORDER_SYSTEM", "SYSTEM"]
    grade: EvidenceGrade
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)

    @model_validator(mode="after")
    def grade_and_source(self) -> SemanticEnvelope:
        kind = getattr(self, "type", "")
        if kind in ("WASH_CYCLE", "OPERATOR_ASSERTION") and self.grade != EvidenceGrade.ASSERTED:
            raise ValueError("Human/efficacy resets must have ASSERTED grade")
        if (
            kind in ("TICKET_BOUND", "TICKET_RELEASED", "OPERATOR_ASSERTION")
            and self.source != "OPERATOR"
        ):
            raise ValueError("This event requires an operator")
        return self


class DraftEnvelope(SemanticEnvelope):
    confidence: float | None = Field(default=None, ge=0, le=1)


class CommittedEnvelope(DraftEnvelope):
    seq: int = Field(ge=0)
    t_committed: int
    late: bool = False


class GradedEnvelope(SemanticEnvelope):
    seq: int = Field(ge=0)
    t_committed: int
    late: bool = False


# CONTRACT-GAP: 12 omits ticket/system/alert payload fields. These typed fields
# transcribe 11/13/16/17/26. Q4 authorizes SUBSTITUTED and SUPPRESSED explicitly.


class ContactBeginFields(Model):
    type: Literal["CONTACT_BEGIN"] = "CONTACT_BEGIN"
    mutates_state: Literal[True] = True
    a: str
    b: str
    contact_point: Point2D


class ContactBegin(ContactBeginFields, CommittedEnvelope):
    """CONTACT_BEGIN CommittedEnvelope projection."""


class DraftContactBegin(ContactBeginFields, DraftEnvelope):
    """CONTACT_BEGIN DraftEnvelope projection."""


class GradedContactBegin(ContactBeginFields, GradedEnvelope):
    """CONTACT_BEGIN GradedEnvelope projection."""


class ContactEndFields(Model):
    type: Literal["CONTACT_END"] = "CONTACT_END"
    mutates_state: Literal[False] = False
    a: str
    b: str
    duration_ms: int


class ContactEnd(ContactEndFields, CommittedEnvelope):
    """CONTACT_END CommittedEnvelope projection."""


class DraftContactEnd(ContactEndFields, DraftEnvelope):
    """CONTACT_END DraftEnvelope projection."""


class GradedContactEnd(ContactEndFields, GradedEnvelope):
    """CONTACT_END GradedEnvelope projection."""


class ZoneEntryFields(Model):
    type: Literal["ZONE_ENTRY"] = "ZONE_ENTRY"
    mutates_state: Literal[True] = True
    carrier: str
    zone: str
    depth: float


class ZoneEntry(ZoneEntryFields, CommittedEnvelope):
    """ZONE_ENTRY CommittedEnvelope projection."""


class DraftZoneEntry(ZoneEntryFields, DraftEnvelope):
    """ZONE_ENTRY DraftEnvelope projection."""


class GradedZoneEntry(ZoneEntryFields, GradedEnvelope):
    """ZONE_ENTRY GradedEnvelope projection."""


class ZoneExitFields(Model):
    type: Literal["ZONE_EXIT"] = "ZONE_EXIT"
    mutates_state: Literal[False] = False
    carrier: str
    zone: str
    dwell_ms: int


class ZoneExit(ZoneExitFields, CommittedEnvelope):
    """ZONE_EXIT CommittedEnvelope projection."""


class DraftZoneExit(ZoneExitFields, DraftEnvelope):
    """ZONE_EXIT DraftEnvelope projection."""


class GradedZoneExit(ZoneExitFields, GradedEnvelope):
    """ZONE_EXIT GradedEnvelope projection."""


class GloveChangeFields(Model):
    type: Literal["GLOVE_CHANGE"] = "GLOVE_CHANGE"
    mutates_state: Literal[True] = True
    worker_slot: int
    phase: Literal["DOFF", "DON"]


class GloveChange(GloveChangeFields, CommittedEnvelope):
    """GLOVE_CHANGE CommittedEnvelope projection."""


class DraftGloveChange(GloveChangeFields, DraftEnvelope):
    """GLOVE_CHANGE DraftEnvelope projection."""


class GradedGloveChange(GloveChangeFields, GradedEnvelope):
    """GLOVE_CHANGE GradedEnvelope projection."""


class ToolSwapFields(Model):
    type: Literal["TOOL_SWAP"] = "TOOL_SWAP"
    mutates_state: Literal[True] = True
    retired: str
    introduced: str
    from_zone: str


class ToolSwap(ToolSwapFields, CommittedEnvelope):
    """TOOL_SWAP CommittedEnvelope projection."""


class DraftToolSwap(ToolSwapFields, DraftEnvelope):
    """TOOL_SWAP DraftEnvelope projection."""


class GradedToolSwap(ToolSwapFields, GradedEnvelope):
    """TOOL_SWAP GradedEnvelope projection."""


class SurfaceSwapFields(Model):
    type: Literal["SURFACE_SWAP"] = "SURFACE_SWAP"
    mutates_state: Literal[True] = True
    retired: str
    introduced: str
    from_zone: str


class SurfaceSwap(SurfaceSwapFields, CommittedEnvelope):
    """SURFACE_SWAP CommittedEnvelope projection."""


class DraftSurfaceSwap(SurfaceSwapFields, DraftEnvelope):
    """SURFACE_SWAP DraftEnvelope projection."""


class GradedSurfaceSwap(SurfaceSwapFields, GradedEnvelope):
    """SURFACE_SWAP GradedEnvelope projection."""


class WashCycleFields(Model):
    type: Literal["WASH_CYCLE"] = "WASH_CYCLE"
    mutates_state: Literal[True] = True
    carrier: str
    zone: str
    duration_ms: int


class WashCycle(WashCycleFields, CommittedEnvelope):
    """WASH_CYCLE CommittedEnvelope projection."""


class DraftWashCycle(WashCycleFields, DraftEnvelope):
    """WASH_CYCLE DraftEnvelope projection."""


class GradedWashCycle(WashCycleFields, GradedEnvelope):
    """WASH_CYCLE GradedEnvelope projection."""


class OperatorAssertionFields(Model):
    type: Literal["OPERATOR_ASSERTION"] = "OPERATOR_ASSERTION"
    mutates_state: Literal[True] = True
    carrier: str
    claim: Literal["CLEAN", "REPLACED"]
    worker_slot: int


class OperatorAssertion(OperatorAssertionFields, CommittedEnvelope):
    """OPERATOR_ASSERTION CommittedEnvelope projection."""


class DraftOperatorAssertion(OperatorAssertionFields, DraftEnvelope):
    """OPERATOR_ASSERTION DraftEnvelope projection."""


class GradedOperatorAssertion(OperatorAssertionFields, GradedEnvelope):
    """OPERATOR_ASSERTION GradedEnvelope projection."""


class SurfaceWipeFields(Model):
    type: Literal["SURFACE_WIPE"] = "SURFACE_WIPE"
    mutates_state: Literal[False] = False
    carrier: str


class SurfaceWipe(SurfaceWipeFields, CommittedEnvelope):
    """SURFACE_WIPE CommittedEnvelope projection."""


class DraftSurfaceWipe(SurfaceWipeFields, DraftEnvelope):
    """SURFACE_WIPE DraftEnvelope projection."""


class GradedSurfaceWipe(SurfaceWipeFields, GradedEnvelope):
    """SURFACE_WIPE GradedEnvelope projection."""


class TicketReceivedFields(Model):
    type: Literal["TICKET_RECEIVED"] = "TICKET_RECEIVED"
    mutates_state: Literal[True] = True
    ticket: str
    items: list[str]
    restrictions: list[Restriction]
    order_source: str = "fixture"


class TicketReceived(TicketReceivedFields, CommittedEnvelope):
    """TICKET_RECEIVED CommittedEnvelope projection."""


class DraftTicketReceived(TicketReceivedFields, DraftEnvelope):
    """TICKET_RECEIVED DraftEnvelope projection."""


class GradedTicketReceived(TicketReceivedFields, GradedEnvelope):
    """TICKET_RECEIVED GradedEnvelope projection."""


class TicketRestrictionResolvedFields(Model):
    type: Literal["TICKET_RESTRICTION_RESOLVED"] = "TICKET_RESTRICTION_RESOLVED"
    mutates_state: Literal[True] = True
    ticket: str
    restrictions: list[Restriction]


class TicketRestrictionResolved(TicketRestrictionResolvedFields, CommittedEnvelope):
    """TICKET_RESTRICTION_RESOLVED CommittedEnvelope projection."""


class DraftTicketRestrictionResolved(TicketRestrictionResolvedFields, DraftEnvelope):
    """TICKET_RESTRICTION_RESOLVED DraftEnvelope projection."""


class GradedTicketRestrictionResolved(TicketRestrictionResolvedFields, GradedEnvelope):
    """TICKET_RESTRICTION_RESOLVED GradedEnvelope projection."""


class TicketBlockedFields(Model):
    type: Literal["TICKET_BLOCKED"] = "TICKET_BLOCKED"
    mutates_state: Literal[True] = True
    ticket: str
    reason: str


class TicketBlocked(TicketBlockedFields, CommittedEnvelope):
    """TICKET_BLOCKED CommittedEnvelope projection."""


class DraftTicketBlocked(TicketBlockedFields, DraftEnvelope):
    """TICKET_BLOCKED DraftEnvelope projection."""


class GradedTicketBlocked(TicketBlockedFields, GradedEnvelope):
    """TICKET_BLOCKED GradedEnvelope projection."""


class TicketBoundFields(Model):
    type: Literal["TICKET_BOUND"] = "TICKET_BOUND"
    mutates_state: Literal[True] = True
    ticket: str
    worker_slot: int
    landing_zone: str | None = None


class TicketBound(TicketBoundFields, CommittedEnvelope):
    """TICKET_BOUND CommittedEnvelope projection."""


class DraftTicketBound(TicketBoundFields, DraftEnvelope):
    """TICKET_BOUND DraftEnvelope projection."""


class GradedTicketBound(TicketBoundFields, GradedEnvelope):
    """TICKET_BOUND GradedEnvelope projection."""


class TicketPrepStartedFields(Model):
    type: Literal["TICKET_PREP_STARTED"] = "TICKET_PREP_STARTED"
    mutates_state: Literal[True] = True
    ticket: str
    landing_zone: str | None = None


class TicketPrepStarted(TicketPrepStartedFields, CommittedEnvelope):
    """TICKET_PREP_STARTED CommittedEnvelope projection."""


class DraftTicketPrepStarted(TicketPrepStartedFields, DraftEnvelope):
    """TICKET_PREP_STARTED DraftEnvelope projection."""


class GradedTicketPrepStarted(TicketPrepStartedFields, GradedEnvelope):
    """TICKET_PREP_STARTED GradedEnvelope projection."""


class TicketItemCompleteFields(Model):
    type: Literal["TICKET_ITEM_COMPLETE"] = "TICKET_ITEM_COMPLETE"
    mutates_state: Literal[True] = True
    ticket: str


class TicketItemComplete(TicketItemCompleteFields, CommittedEnvelope):
    """TICKET_ITEM_COMPLETE CommittedEnvelope projection."""


class DraftTicketItemComplete(TicketItemCompleteFields, DraftEnvelope):
    """TICKET_ITEM_COMPLETE DraftEnvelope projection."""


class GradedTicketItemComplete(TicketItemCompleteFields, GradedEnvelope):
    """TICKET_ITEM_COMPLETE GradedEnvelope projection."""


class TicketHeldFields(Model):
    type: Literal["TICKET_HELD"] = "TICKET_HELD"
    mutates_state: Literal[True] = True
    ticket: str
    alert_id: str


class TicketHeld(TicketHeldFields, CommittedEnvelope):
    """TICKET_HELD CommittedEnvelope projection."""


class DraftTicketHeld(TicketHeldFields, DraftEnvelope):
    """TICKET_HELD DraftEnvelope projection."""


class GradedTicketHeld(TicketHeldFields, GradedEnvelope):
    """TICKET_HELD GradedEnvelope projection."""


class TicketReleasedFields(Model):
    type: Literal["TICKET_RELEASED"] = "TICKET_RELEASED"
    mutates_state: Literal[True] = True
    ticket: str
    worker_slot: int


class TicketReleased(TicketReleasedFields, CommittedEnvelope):
    """TICKET_RELEASED CommittedEnvelope projection."""


class DraftTicketReleased(TicketReleasedFields, DraftEnvelope):
    """TICKET_RELEASED DraftEnvelope projection."""


class GradedTicketReleased(TicketReleasedFields, GradedEnvelope):
    """TICKET_RELEASED GradedEnvelope projection."""


class TicketVoidedFields(Model):
    type: Literal["TICKET_VOIDED"] = "TICKET_VOIDED"
    mutates_state: Literal[True] = True
    ticket: str
    reason: str


class TicketVoided(TicketVoidedFields, CommittedEnvelope):
    """TICKET_VOIDED CommittedEnvelope projection."""


class DraftTicketVoided(TicketVoidedFields, DraftEnvelope):
    """TICKET_VOIDED DraftEnvelope projection."""


class GradedTicketVoided(TicketVoidedFields, GradedEnvelope):
    """TICKET_VOIDED GradedEnvelope projection."""


class TicketReworkOpenedFields(Model):
    type: Literal["TICKET_REWORK_OPENED"] = "TICKET_REWORK_OPENED"
    mutates_state: Literal[True] = True
    ticket: str
    rework_of: str
    items: list[str]
    restrictions: list[Restriction]


class TicketReworkOpened(TicketReworkOpenedFields, CommittedEnvelope):
    """TICKET_REWORK_OPENED CommittedEnvelope projection."""


class DraftTicketReworkOpened(TicketReworkOpenedFields, DraftEnvelope):
    """TICKET_REWORK_OPENED DraftEnvelope projection."""


class GradedTicketReworkOpened(TicketReworkOpenedFields, GradedEnvelope):
    """TICKET_REWORK_OPENED GradedEnvelope projection."""


class TicketItemSubstitutedFields(Model):
    type: Literal["TICKET_ITEM_SUBSTITUTED"] = "TICKET_ITEM_SUBSTITUTED"
    mutates_state: Literal[True] = True
    ticket: str
    items: list[str]


class TicketItemSubstituted(TicketItemSubstitutedFields, CommittedEnvelope):
    """TICKET_ITEM_SUBSTITUTED CommittedEnvelope projection."""


class DraftTicketItemSubstituted(TicketItemSubstitutedFields, DraftEnvelope):
    """TICKET_ITEM_SUBSTITUTED DraftEnvelope projection."""


class GradedTicketItemSubstituted(TicketItemSubstitutedFields, GradedEnvelope):
    """TICKET_ITEM_SUBSTITUTED GradedEnvelope projection."""


class StationModeChangedFields(Model):
    type: Literal["STATION_MODE_CHANGED"] = "STATION_MODE_CHANGED"
    mutates_state: Literal[True] = True
    mode: Mode
    cause: str


class StationModeChanged(StationModeChangedFields, CommittedEnvelope):
    """STATION_MODE_CHANGED CommittedEnvelope projection."""


class DraftStationModeChanged(StationModeChangedFields, DraftEnvelope):
    """STATION_MODE_CHANGED DraftEnvelope projection."""


class GradedStationModeChanged(StationModeChangedFields, GradedEnvelope):
    """STATION_MODE_CHANGED GradedEnvelope projection."""


class CarrierObservabilityChangedFields(Model):
    type: Literal["CARRIER_OBSERVABILITY_CHANGED"] = "CARRIER_OBSERVABILITY_CHANGED"
    mutates_state: Literal[True] = True
    carrier: str
    epistemic: EpistemicStatus
    cause: str


class CarrierObservabilityChanged(CarrierObservabilityChangedFields, CommittedEnvelope):
    """CARRIER_OBSERVABILITY_CHANGED CommittedEnvelope projection."""


class DraftCarrierObservabilityChanged(CarrierObservabilityChangedFields, DraftEnvelope):
    """CARRIER_OBSERVABILITY_CHANGED DraftEnvelope projection."""


class GradedCarrierObservabilityChanged(CarrierObservabilityChangedFields, GradedEnvelope):
    """CARRIER_OBSERVABILITY_CHANGED GradedEnvelope projection."""


class TrackIdentitySuspectFields(Model):
    type: Literal["TRACK_IDENTITY_SUSPECT"] = "TRACK_IDENTITY_SUSPECT"
    mutates_state: Literal[True] = True
    a: str
    b: str
    cause: str


class TrackIdentitySuspect(TrackIdentitySuspectFields, CommittedEnvelope):
    """TRACK_IDENTITY_SUSPECT CommittedEnvelope projection."""


class DraftTrackIdentitySuspect(TrackIdentitySuspectFields, DraftEnvelope):
    """TRACK_IDENTITY_SUSPECT DraftEnvelope projection."""


class GradedTrackIdentitySuspect(TrackIdentitySuspectFields, GradedEnvelope):
    """TRACK_IDENTITY_SUSPECT GradedEnvelope projection."""


class ConfigLoadedFields(Model):
    type: Literal["CONFIG_LOADED"] = "CONFIG_LOADED"
    mutates_state: Literal[True] = True
    config_version: str
    knowledge_version: str


class ConfigLoaded(ConfigLoadedFields, CommittedEnvelope):
    """CONFIG_LOADED CommittedEnvelope projection."""


class DraftConfigLoaded(ConfigLoadedFields, DraftEnvelope):
    """CONFIG_LOADED DraftEnvelope projection."""


class GradedConfigLoaded(ConfigLoadedFields, GradedEnvelope):
    """CONFIG_LOADED GradedEnvelope projection."""


class HealthDegradedFields(Model):
    type: Literal["HEALTH_DEGRADED"] = "HEALTH_DEGRADED"
    mutates_state: Literal[False] = False
    cause: str
    rejected_event_id: str | None = None


class HealthDegraded(HealthDegradedFields, CommittedEnvelope):
    """HEALTH_DEGRADED CommittedEnvelope projection."""


class DraftHealthDegraded(HealthDegradedFields, DraftEnvelope):
    """HEALTH_DEGRADED DraftEnvelope projection."""


class GradedHealthDegraded(HealthDegradedFields, GradedEnvelope):
    """HEALTH_DEGRADED GradedEnvelope projection."""


class AlertRaisedFields(Model):
    type: Literal["ALERT_RAISED"] = "ALERT_RAISED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertRaised(AlertRaisedFields, CommittedEnvelope):
    """ALERT_RAISED CommittedEnvelope projection."""


class DraftAlertRaised(AlertRaisedFields, DraftEnvelope):
    """ALERT_RAISED DraftEnvelope projection."""


class GradedAlertRaised(AlertRaisedFields, GradedEnvelope):
    """ALERT_RAISED GradedEnvelope projection."""


class AlertUpdatedFields(Model):
    type: Literal["ALERT_UPDATED"] = "ALERT_UPDATED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertUpdated(AlertUpdatedFields, CommittedEnvelope):
    """ALERT_UPDATED CommittedEnvelope projection."""


class DraftAlertUpdated(AlertUpdatedFields, DraftEnvelope):
    """ALERT_UPDATED DraftEnvelope projection."""


class GradedAlertUpdated(AlertUpdatedFields, GradedEnvelope):
    """ALERT_UPDATED GradedEnvelope projection."""


class AlertAcknowledgedFields(Model):
    type: Literal["ALERT_ACKNOWLEDGED"] = "ALERT_ACKNOWLEDGED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertAcknowledged(AlertAcknowledgedFields, CommittedEnvelope):
    """ALERT_ACKNOWLEDGED CommittedEnvelope projection."""


class DraftAlertAcknowledged(AlertAcknowledgedFields, DraftEnvelope):
    """ALERT_ACKNOWLEDGED DraftEnvelope projection."""


class GradedAlertAcknowledged(AlertAcknowledgedFields, GradedEnvelope):
    """ALERT_ACKNOWLEDGED GradedEnvelope projection."""


class AlertResolvedFields(Model):
    type: Literal["ALERT_RESOLVED"] = "ALERT_RESOLVED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertResolved(AlertResolvedFields, CommittedEnvelope):
    """ALERT_RESOLVED CommittedEnvelope projection."""


class DraftAlertResolved(AlertResolvedFields, DraftEnvelope):
    """ALERT_RESOLVED DraftEnvelope projection."""


class GradedAlertResolved(AlertResolvedFields, GradedEnvelope):
    """ALERT_RESOLVED GradedEnvelope projection."""


class AlertEscalatedFields(Model):
    type: Literal["ALERT_ESCALATED"] = "ALERT_ESCALATED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertEscalated(AlertEscalatedFields, CommittedEnvelope):
    """ALERT_ESCALATED CommittedEnvelope projection."""


class DraftAlertEscalated(AlertEscalatedFields, DraftEnvelope):
    """ALERT_ESCALATED DraftEnvelope projection."""


class GradedAlertEscalated(AlertEscalatedFields, GradedEnvelope):
    """ALERT_ESCALATED GradedEnvelope projection."""


class AlertExpiredFields(Model):
    type: Literal["ALERT_EXPIRED"] = "ALERT_EXPIRED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertExpired(AlertExpiredFields, CommittedEnvelope):
    """ALERT_EXPIRED CommittedEnvelope projection."""


class DraftAlertExpired(AlertExpiredFields, DraftEnvelope):
    """ALERT_EXPIRED DraftEnvelope projection."""


class GradedAlertExpired(AlertExpiredFields, GradedEnvelope):
    """ALERT_EXPIRED GradedEnvelope projection."""


class AlertSuppressedFields(Model):
    type: Literal["ALERT_SUPPRESSED"] = "ALERT_SUPPRESSED"
    mutates_state: Literal[False] = False
    alert_id: str
    pathway_signature: str
    command: AlertCommand | None = None
    worker_slot: int | None = None


class AlertSuppressed(AlertSuppressedFields, CommittedEnvelope):
    """ALERT_SUPPRESSED CommittedEnvelope projection."""


class DraftAlertSuppressed(AlertSuppressedFields, DraftEnvelope):
    """ALERT_SUPPRESSED DraftEnvelope projection."""


class GradedAlertSuppressed(AlertSuppressedFields, GradedEnvelope):
    """ALERT_SUPPRESSED GradedEnvelope projection."""


Event = Annotated[
    ContactBegin
    | ContactEnd
    | ZoneEntry
    | ZoneExit
    | GloveChange
    | ToolSwap
    | SurfaceSwap
    | WashCycle
    | OperatorAssertion
    | SurfaceWipe
    | TicketReceived
    | TicketRestrictionResolved
    | TicketBlocked
    | TicketBound
    | TicketPrepStarted
    | TicketItemComplete
    | TicketHeld
    | TicketReleased
    | TicketVoided
    | TicketReworkOpened
    | TicketItemSubstituted
    | StationModeChanged
    | CarrierObservabilityChanged
    | TrackIdentitySuspect
    | ConfigLoaded
    | HealthDegraded
    | AlertRaised
    | AlertUpdated
    | AlertAcknowledged
    | AlertResolved
    | AlertEscalated
    | AlertExpired
    | AlertSuppressed,
    Field(discriminator="type"),
]
EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)

DraftEvent = Annotated[
    DraftContactBegin
    | DraftContactEnd
    | DraftZoneEntry
    | DraftZoneExit
    | DraftGloveChange
    | DraftToolSwap
    | DraftSurfaceSwap
    | DraftWashCycle
    | DraftOperatorAssertion
    | DraftSurfaceWipe
    | DraftTicketReceived
    | DraftTicketRestrictionResolved
    | DraftTicketBlocked
    | DraftTicketBound
    | DraftTicketPrepStarted
    | DraftTicketItemComplete
    | DraftTicketHeld
    | DraftTicketReleased
    | DraftTicketVoided
    | DraftTicketReworkOpened
    | DraftTicketItemSubstituted
    | DraftStationModeChanged
    | DraftCarrierObservabilityChanged
    | DraftTrackIdentitySuspect
    | DraftConfigLoaded
    | DraftHealthDegraded
    | DraftAlertRaised
    | DraftAlertUpdated
    | DraftAlertAcknowledged
    | DraftAlertResolved
    | DraftAlertEscalated
    | DraftAlertExpired
    | DraftAlertSuppressed,
    Field(discriminator="type"),
]
DRAFTEVENT_ADAPTER: TypeAdapter[DraftEvent] = TypeAdapter(DraftEvent)

GradedEvent = Annotated[
    GradedContactBegin
    | GradedContactEnd
    | GradedZoneEntry
    | GradedZoneExit
    | GradedGloveChange
    | GradedToolSwap
    | GradedSurfaceSwap
    | GradedWashCycle
    | GradedOperatorAssertion
    | GradedSurfaceWipe
    | GradedTicketReceived
    | GradedTicketRestrictionResolved
    | GradedTicketBlocked
    | GradedTicketBound
    | GradedTicketPrepStarted
    | GradedTicketItemComplete
    | GradedTicketHeld
    | GradedTicketReleased
    | GradedTicketVoided
    | GradedTicketReworkOpened
    | GradedTicketItemSubstituted
    | GradedStationModeChanged
    | GradedCarrierObservabilityChanged
    | GradedTrackIdentitySuspect
    | GradedConfigLoaded
    | GradedHealthDegraded
    | GradedAlertRaised
    | GradedAlertUpdated
    | GradedAlertAcknowledged
    | GradedAlertResolved
    | GradedAlertEscalated
    | GradedAlertExpired
    | GradedAlertSuppressed,
    Field(discriminator="type"),
]
GRADEDEVENT_ADAPTER: TypeAdapter[GradedEvent] = TypeAdapter(GradedEvent)

EVENT_TYPES = (
    "CONTACT_BEGIN",
    "CONTACT_END",
    "ZONE_ENTRY",
    "ZONE_EXIT",
    "GLOVE_CHANGE",
    "TOOL_SWAP",
    "SURFACE_SWAP",
    "WASH_CYCLE",
    "OPERATOR_ASSERTION",
    "SURFACE_WIPE",
    "TICKET_RECEIVED",
    "TICKET_RESTRICTION_RESOLVED",
    "TICKET_BLOCKED",
    "TICKET_BOUND",
    "TICKET_PREP_STARTED",
    "TICKET_ITEM_COMPLETE",
    "TICKET_HELD",
    "TICKET_RELEASED",
    "TICKET_VOIDED",
    "TICKET_REWORK_OPENED",
    "TICKET_ITEM_SUBSTITUTED",
    "STATION_MODE_CHANGED",
    "CARRIER_OBSERVABILITY_CHANGED",
    "TRACK_IDENTITY_SUSPECT",
    "CONFIG_LOADED",
    "HEALTH_DEGRADED",
    "ALERT_RAISED",
    "ALERT_UPDATED",
    "ALERT_ACKNOWLEDGED",
    "ALERT_RESOLVED",
    "ALERT_ESCALATED",
    "ALERT_EXPIRED",
    "ALERT_SUPPRESSED",
)
