"""The state-snapshot wire shape pushed at 5Hz and read by both routes (22 `WorkerDisplay`,
25 §Inspector). `state_summary` + `interventions` are Device A's `DisplayPayload` exactly
(src/domain: StationSummary, Alert); B adds a `runtime` block for what only the composition
root knows: clock, health, the committed-log tail, zone geometry and the menu. Exactly three
epistemic values (13); no SAFE anywhere (02); no identity fields (24).

`python -m src.ui.wire` regenerates `static/mock/snapshot.schema.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.domain import Alert, EvidenceGrade, StationSummary, ZoneKind


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


class EventLine(Wire):
    seq: int
    event_id: str
    t_occurred: int
    type: str
    source: str
    grade: EvidenceGrade | None
    participants: list[str]
    mutates_state: bool
    late: bool
    summary: str


class ZoneInfo(Wire):
    zone_id: str
    kind: ZoneKind
    contents: list[str]
    bound_carrier: str | None
    allergens: list[str]  # from zone_allergens; what a container "holds"
    polygon: list[tuple[float, float]]
    last_contact_at: int | None


class MenuItem(Wire):
    item_id: str
    display_name: str


class RuntimeInfo(Wire):
    time: TimeRef
    seq: int
    health: Health
    recent_events: list[EventLine]  # tail of the committed log, oldest first
    zones: list[ZoneInfo]
    menu: list[MenuItem]
    config_checksum: str
    knowledge_checksum: str
    rejected: list[str] = []


class Snapshot(Wire):
    schema_version: Literal[1]
    state_summary: StationSummary
    interventions: list[Alert]
    runtime: RuntimeInfo


SCHEMA_PATH = Path(__file__).parent / "static" / "mock" / "snapshot.schema.json"

if __name__ == "__main__":
    SCHEMA_PATH.write_text(json.dumps(Snapshot.model_json_schema(), indent=2) + "\n")
    sys.stdout.write(f"wrote {SCHEMA_PATH}\n")
