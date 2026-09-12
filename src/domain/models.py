"""Shared semantic types; imports no project package (11–19)."""
from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Timestamp = int  # CONTRACT-GAP: timestamp representation omitted; scenario milliseconds (36).
CarrierId = str
AllergenId = str
ZoneId = str
TicketId = str
StationId = str
Seq = int
AlertKey = str
KnowledgeVersion = str


class Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceGrade(StrEnum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    ASSERTED = "ASSERTED"
    PESSIMISTIC = "PESSIMISTIC"


GRADE_RANK = {g: 3 - i for i, g in enumerate(EvidenceGrade)}


class EpistemicStatus(StrEnum):
    TRACKED = "TRACKED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class CarrierKind(StrEnum):
    GLOVES = "GLOVES"
    TOOL = "TOOL"
    SURFACE = "SURFACE"
    CONTAINER = "CONTAINER"
    FOOD = "FOOD"


class ResetKind(StrEnum):
    GLOVE_CHANGE = "GLOVE_CHANGE"
    TOOL_SWAP = "TOOL_SWAP"
    SURFACE_SWAP = "SURFACE_SWAP"
    WASH_CYCLE = "WASH_CYCLE"
    OPERATOR_ASSERTION = "OPERATOR_ASSERTION"


class Strength(StrEnum):
    PRESENT = "PRESENT"
    POSSIBLE = "POSSIBLE"


class Mode(StrEnum):
    FULL = "FULL"
    PROTOCOL_ONLY = "PROTOCOL_ONLY"
    REPLAY = "REPLAY"
    CALIBRATION = "CALIBRATION"


class ZoneKind(StrEnum):
    INGREDIENT = "INGREDIENT"
    TOOL_RACK = "TOOL_RACK"
    WORK = "WORK"
    LANDING = "LANDING"
    GLOVE_DISPENSER = "GLOVE_DISPENSER"
    WASH = "WASH"
    CLEAN_STOCK = "CLEAN_STOCK"


class TicketLifecycle(StrEnum):
    RECEIVED = "RECEIVED"
    BLOCKED = "BLOCKED"
    BOUND = "BOUND"
    IN_PREP = "IN_PREP"
    COMPLETE = "COMPLETE"
    HELD = "HELD"
    RELEASED = "RELEASED"
    VOIDED = "VOIDED"


class Resolution(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVABLE = "UNRESOLVABLE"


class Point2D(Model):
    x: float
    y: float


class TaintRecord(Model):
    allergen_id: str
    acquired_at: Timestamp
    source_event_id: str
    source_carrier_id: str
    grade: EvidenceGrade
    hops: int = Field(ge=0)
    strength: Strength = Strength.PRESENT


class Carrier(Model):
    carrier_id: str
    kind: CarrierKind
    taints: dict[str, TaintRecord] = Field(default_factory=dict)
    epistemic: EpistemicStatus = EpistemicStatus.UNKNOWN
    last_observed_at: Timestamp | None = None
    home_zone: str | None = None
    resettable_by: frozenset[ResetKind] = frozenset()
    # CONTRACT-GAP: 13 requires asserted_at/clean grade; retained separately from taint.
    asserted_at: Timestamp | None = None
    clean_grade: EvidenceGrade | None = None
    worker_slot: int | None = None

    @model_validator(mode="after")
    def food_cannot_reset(self) -> Carrier:
        if self.kind == CarrierKind.FOOD and self.resettable_by:
            raise ValueError("FOOD has no valid reset")
        return self


class Zone(Model):
    zone_id: str
    polygon: list[Point2D] = Field(default_factory=list)
    kind: ZoneKind
    contents: list[str] = Field(default_factory=list)
    bound_carrier: str | None = None


class Restriction(Model):
    kind: Literal["AVOID_ALLERGEN", "AVOID_INGREDIENT", "DIETARY"] = "AVOID_ALLERGEN"
    allergen_ids: frozenset[str] = frozenset()
    raw_text: str
    resolution: Resolution = Resolution.AMBIGUOUS
    severity_declared: Literal["STATED_ALLERGY", "STATED_PREFERENCE", "UNSPECIFIED"] = "UNSPECIFIED"


class Ticket(Model):
    ticket_id: str
    items: list[str]
    restrictions: list[Restriction] = Field(default_factory=list)
    source: str = "fixture"
    lifecycle: TicketLifecycle = TicketLifecycle.RECEIVED
    bound_station: str | None = None
    bound_at: Timestamp | None = None
    rework_of: str | None = None
    landing_zone: str | None = None


class Station(Model):
    station_id: str
    config_version: str
    knowledge_version: str
    mode: Mode
    carriers: dict[str, Carrier] = Field(default_factory=dict)
    zones: dict[str, Zone] = Field(default_factory=dict)
    bound_tickets: list[str] = Field(default_factory=list)
    worker_slots: int = Field(ge=0)
    recent_allergen_exposure: dict[str, Timestamp] = Field(default_factory=dict)


class AllergenNode(Model):
    id: str
    display_name: str
    parents: list[str] = Field(default_factory=list)
    regulatory_class: str | None = None


class IngredientRecord(Model):
    ingredient_id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    contains: frozenset[str] = frozenset()
    may_contain: frozenset[str] = frozenset()
    source: Literal["SUPPLIER_LABEL", "HOUSE_RECIPE", "MANUAL"]
    verified_at: str
    verified_by_role: str


class MenuItemRecord(Model):
    item_id: str
    ingredient_ids: list[str]
    required_zones: list[str]
    station_id: str


class Knowledge(Model):
    knowledge_version: str
    allergens: dict[str, AllergenNode]
    ingredients: dict[str, IngredientRecord]
    menu_items: dict[str, MenuItemRecord]


class Config(Model):
    # CONTRACT-GAP: 31 omits concrete layout. Flat millisecond windows; values supplied by B.
    config_version: str
    knowledge_version: str
    max_hops: int = Field(ge=0)
    t_reorder: int = Field(ge=0)
    t_stale: dict[CarrierKind, int]
    t_occlusion_max: int = Field(ge=0)
    station_recent_window: int = Field(ge=0)
    t_escalate: int = Field(ge=0)
    t_cooldown: int = Field(ge=0)
    t_abandon: int = Field(ge=0)
    t_dwell: int = Field(ge=0)
    t_hysteresis: int = Field(ge=0)
    t_recover: int = Field(ge=0)
    t_manager: int = Field(ge=0)
    threshold_observed: dict[str, float]
    threshold_inferred: dict[str, float]
    normalizer_threshold: float = Field(ge=0, le=1)
    strength_decay_per_hop: list[Strength]


class StationConfig(Model):
    station_id: str
    config_version: str
    knowledge_version: str
    mode: Mode
    worker_slots: int = Field(ge=0)
    carriers: dict[str, Carrier]
    zones: dict[str, Zone]
    # CONTRACT-GAP: initial has no Knowledge argument; loader supplies resolved zone profiles.
    zone_allergens: dict[str, dict[str, Strength]] = Field(default_factory=dict)
    calibration: dict[str, JsonValue] = Field(default_factory=dict)


class StateDelta(Model):
    event_id: str
    rule_id: str
    carrier_id: str | None = None
    field: str
    before: JsonValue = None
    after: JsonValue = None


class ContactEdge(Model):
    event_id: str
    t_occurred: Timestamp
    a: str
    b: str
    grade: EvidenceGrade


class ResetRecord(Model):
    event_id: str
    t_occurred: Timestamp
    carrier_id: str
    grade: EvidenceGrade
    operator: bool = False


class WorldState(Model):
    station: Station
    tickets: dict[str, Ticket] = Field(default_factory=dict)
    contacts: list[ContactEdge] = Field(default_factory=list)
    resets: list[ResetRecord] = Field(default_factory=list)
    # Acquisition history survives resets for structural pathway reconstruction.
    acquisitions: dict[str, list[TaintRecord]] = Field(default_factory=dict)
    zone_allergens: dict[str, dict[str, Strength]] = Field(default_factory=dict)
    event_ids: list[str] = Field(default_factory=list)
    deltas: list[StateDelta] = Field(default_factory=list)
    t_occurred: Timestamp = 0
    last_event_type: str = ""
    last_event_id: str = ""
    last_event_source: str = "SYSTEM"
    conditions: list[str] = Field(default_factory=list)


class Pathway(Model):
    allergen_id: str
    nodes: list[str]
    event_ids: list[str]
    grade: EvidenceGrade
    hops: int
    broken: bool = False
    strength: Strength = Strength.PRESENT


class RiskLevel(StrEnum):
    CLEAR = "CLEAR"
    UNVERIFIED = "UNVERIFIED"
    PATHWAY_OPEN = "PATHWAY_OPEN"
    PATHWAY_RESOLVED = "PATHWAY_RESOLVED"


class RiskAssessment(Model):
    ticket_id: str
    allergen_id: str
    level: RiskLevel
    pathways: list[Pathway] = Field(default_factory=list)
    blocking_carriers: list[str] = Field(default_factory=list)
    max_grade: EvidenceGrade
    assessed_at: Timestamp
    config_version: str
    knowledge_version: str
    # CONTRACT-GAP: 15 tier rules need lifecycle; Q1 ruling authorizes this field.
    ticket_lifecycle: TicketLifecycle
    station_id: str
    mode: Mode
    cause_event_id: str
    cause_event_type: str
    operator_resolution: bool = False
    resolution_reason: Literal["RESOLVED_BY_RESET", "RESOLVED_BY_ASSERTION", "RESOLVED_BY_REMAKE"] | None = None
    condition: str | None = None


class Tier(IntEnum):
    RESET = 0
    INTERRUPT = 1
    HOLD = 2


class AlertLifecycle(StrEnum):
    RAISED = "RAISED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    RESOLVED_BY_RESET = "RESOLVED_BY_RESET"
    RESOLVED_BY_ASSERTION = "RESOLVED_BY_ASSERTION"
    RESOLVED_BY_REMAKE = "RESOLVED_BY_REMAKE"
    EXPIRED = "EXPIRED"


class Action(Model):
    kind: Literal["NEW_GLOVES", "SWAP_TOOL", "SWAP_SURFACE", "USE_SEALED_BACKUP", "VERIFY", "SEQUENCE_TICKETS", "HOLD", "REMAKE"]
    carrier_id: str | None = None
    label: str


class TraceStep(Model):
    event_id: str
    t_occurred: Timestamp
    rule_id: str
    state_delta: StateDelta
    grade: EvidenceGrade
    narrative: str


class Alert(Model):
    alert_id: str
    alert_key: str
    pathway_signature: str
    tier: Tier
    ticket_id: str
    allergen_id: str
    headline: str
    required_actions: list[Action]
    derivation: list[TraceStep]
    raised_at: Timestamp
    state: AlertLifecycle
    acknowledged_by_slot: int | None = None
    blocking_carriers: list[str] = Field(default_factory=list)
    updated_at: Timestamp


class AlertCommand(Model):
    # CONTRACT-GAP: 22 names commands without fields; full alert plus event-time provenance.
    kind: Literal["RAISE", "UPDATE", "RESOLVE", "ESCALATE", "SUPPRESS"]
    alert: Alert
    t_occurred: Timestamp
    cause_event_id: str
    operator: bool = False
    cooldown_until: Timestamp | None = None


class RawOrder(Model):
    external_id: str
    items: list[str]
    notes: list[str]
    received_at: Timestamp


class HealthStatus(Model):
    healthy: bool
    causes: list[str] = Field(default_factory=list)


class WorkerAction(Model):
    # CONTRACT-GAP: 22/26 omit payload fields; action discriminant and explicit targets.
    action: Literal["BIND", "ACKNOWLEDGE", "ALREADY_CLEAN", "ALREADY_SWAPPED", "DISMISS", "REMAKE", "RESOLVE_HOLD", "PREP_START", "ITEM_COMPLETE", "RESOLVE_RESTRICTION"]
    worker_slot: int
    ticket_id: str | None = None
    carrier_id: str | None = None
    alert_id: str | None = None
    raw_text: str | None = None


class StationSummary(Model):
    # CONTRACT-GAP: 22 omits wire fields; mirror the station and ticket projection.
    station_id: str
    mode: Mode
    config_version: str
    knowledge_version: str
    carriers: list[Carrier]
    tickets: list[Ticket]
    conditions: list[str]
    t_occurred: Timestamp


class DisplayPayload(Model):
    state_summary: StationSummary
    interventions: list[Alert]
