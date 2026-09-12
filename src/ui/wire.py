"""The state-snapshot wire shape — `22` `WorkerDisplay.render(interventions, state_summary)`.

Published first by Device B (the early publisher's shape wins). The runtime projects A's
`WorldState`, tickets and `AlertState` into a `Snapshot` and pushes it whole at 5Hz; `/` and
`/inspector` both read it, so the inspector never has a privileged view (25). Exactly three
epistemic values (13). No `SAFE` member anywhere (02). No identity fields (24, ADR-0010).
Headlines are ≤ 6 words and structurally cannot carry a prohibited claim word (02, 16).

`python -m src.ui.wire` regenerates `static/mock/snapshot.schema.json`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

Mode = Literal["FULL", "PROTOCOL_ONLY", "REPLAY", "CALIBRATION"]
Epistemic = Literal["TRACKED", "STALE", "UNKNOWN"]
Grade = Literal["OBSERVED", "INFERRED", "ASSERTED", "PESSIMISTIC"]
Strength = Literal["PRESENT", "POSSIBLE"]
CarrierKind = Literal["GLOVES", "TOOL", "SURFACE", "CONTAINER", "FOOD"]
ZoneKind = Literal[
    "INGREDIENT", "TOOL_RACK", "CLEAN_STOCK", "WORK", "LANDING", "GLOVE_DISPENSER", "WASH"
]
Lifecycle = Literal[
    "RECEIVED", "BLOCKED", "BOUND", "IN_PREP", "COMPLETE", "HELD", "RELEASED", "VOIDED"
]
Resolution = Literal["RESOLVED", "AMBIGUOUS", "UNRESOLVABLE"]
RestrictionKind = Literal["AVOID_ALLERGEN", "AVOID_INGREDIENT", "DIETARY"]
Severity = Literal["STATED_ALLERGY", "STATED_PREFERENCE", "UNSPECIFIED"]
AlertLifecycle = Literal[
    "RAISED",
    "ACKNOWLEDGED",
    "ESCALATED",
    "RESOLVED_BY_RESET",
    "RESOLVED_BY_ASSERTION",
    "RESOLVED_BY_REMAKE",
    "EXPIRED",
]
ActionKind = Literal[
    "NEW_GLOVES", "SWAP_TOOL", "SWAP_SURFACE", "USE_SEALED_BACKUP", "SEQUENCE_TICKETS"
]
Source = Literal["PERCEPTION", "OPERATOR", "ORDER_SYSTEM", "SYSTEM"]

# 02 §Unsupported claims. "clean" alone is permitted: 26's approved copy uses it.
PROHIBITED_CLAIMS = re.compile(
    r"\bsafe\b|\bunsafe\b|\bcontaminat\w*|allergen[- ]free|\bsanitiz\w*|\bdisinfect\w*", re.I
)


class Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TimeRef(Wire):
    t: int  # ms. WALL = Unix epoch ms (SystemClock); LOG = ms from log start (LogClock)
    kind: Literal["WALL", "LOG"]


class Health(Wire):
    vision: Literal["OK", "DEGRADED", "UNAVAILABLE"]
    reasoning: Literal["OK", "DOWN"]
    late_rate: float = 0.0  # fraction of committed events flagged late (19)
    rejected_events: int = 0  # quarantined at append (23 P10)
    message: str | None = None  # the specific error when CALIBRATION refuses FULL (23 P12)
    last_incident_event_id: str | None = None  # 23 P11


class Taint(Wire):
    allergen_id: str
    grade: Grade
    strength: Strength
    hops: int
    acquired_at: int
    source_event_id: str
    source_carrier_id: str | None = None


class Carrier(Wire):
    carrier_id: str
    kind: CarrierKind
    epistemic: Epistemic
    last_observed_at: int | None
    home_zone: str | None
    taints: list[Taint]
    source_allergens: list[str] = []  # CONTAINER bound to an INGREDIENT zone: its own contents
    shared: bool = False  # shared container — affects all future tickets (37 beat 2)
    last_wiped_at: int | None = None  # from the log, for explanation only (ADR-0009)
    asserted_at: int | None = None  # last OPERATOR_ASSERTION on this carrier


class Restriction(Wire):
    raw_text: str
    kind: RestrictionKind
    resolution: Resolution
    allergen_ids: list[str]
    severity_declared: Severity


class TicketItem(Wire):
    item_id: str
    display_name: str


class Ticket(Wire):
    ticket_id: str
    lifecycle: Lifecycle
    items: list[TicketItem]
    restrictions: list[Restriction]
    bound_at: int | None
    rework_of: str | None = None
    food_carrier: str | None = None  # `food:<ticket_id>` while IN_PREP..HELD (11)


class RequiredAction(Wire):
    action: ActionKind
    carrier_id: str | None
    label: str  # icon + noun, e.g. "New gloves"
    done: bool  # ticks itself off as resets are observed/asserted (26)


class TraceStep(Wire):
    kind: Literal["EVENT", "ABSENCE", "RULE", "ALERT"]
    t_occurred: int | None
    event_id: str | None
    type: str | None  # event type for EVENT; rule id for RULE
    grade: Grade | None
    narrative: str  # template-generated, never free text (25)
    state_delta: str | None


class Alert(Wire):
    alert_id: str
    alert_key: str
    pathway_signature: str
    tier: Literal[0, 1, 2]
    ticket_id: str
    allergen_id: str
    headline: str  # <= 6 words (16, 26)
    body: str | None
    state: AlertLifecycle
    raised_at: int
    acknowledged_by_slot: int | None
    required_actions: list[RequiredAction]
    derivation: list[TraceStep]
    dismissed_until: int | None = None  # display suppressed, state unchanged (26)

    @field_validator("headline")
    @classmethod
    def _six_words_no_claims(cls, v: str) -> str:
        words = [w for w in v.split() if re.search(r"[A-Za-z0-9]", w)]
        if len(words) > 6:
            raise ValueError("headline must be <= 6 words (26)")
        if PROHIBITED_CLAIMS.search(v):
            raise ValueError("headline carries a prohibited claim word (02)")
        return v

    @field_validator("body")
    @classmethod
    def _no_claims(cls, v: str | None) -> str | None:
        if v and PROHIBITED_CLAIMS.search(v):
            raise ValueError("body carries a prohibited claim word (02)")
        return v


class EventLine(Wire):
    seq: int
    event_id: str
    t_occurred: int
    type: str
    source: Source
    grade: Grade | None
    participants: list[str]
    mutates_state: bool
    late: bool
    summary: str


class Zone(Wire):
    zone_id: str
    kind: ZoneKind
    contents: list[str]
    bound_carrier: str | None
    polygon: list[tuple[int, int]]
    last_contact_at: int | None


class Condition(Wire):
    multi_restriction: bool = False  # 17 §Concurrency


class Snapshot(Wire):
    schema_version: Literal[1]
    menu: list[TicketItem]  # bindable items (18 §3); static per knowledge version
    station_id: str
    mode: Mode
    time: TimeRef
    seq: int
    config_version: int
    knowledge_version: int
    worker_slots: int  # count only; never identity (24)
    health: Health
    condition: Condition
    carriers: list[Carrier]
    tickets: list[Ticket]
    alerts: list[Alert]
    recent_events: list[EventLine]  # tail of the committed log, oldest first
    zones: list[Zone]


SCHEMA_PATH = Path(__file__).parent / "static" / "mock" / "snapshot.schema.json"

if __name__ == "__main__":
    SCHEMA_PATH.write_text(json.dumps(Snapshot.model_json_schema(), indent=2) + "\n")
    sys.stdout.write(f"wrote {SCHEMA_PATH}\n")
