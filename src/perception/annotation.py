"""Video annotation schema (35 §Annotation schema), implemented verbatim.

Annotation is at the *event* level, never the frame level: a clip's ground truth is the
list of events perception is obliged to emit (21) plus the intervals during which a carrier
was truly unobservable — the ground truth for occlusion-reporting recall (34), the perception
metric that matters most. `scripts/record_fixture.py` writes the skeleton; a person fills
`events`, `occlusion_intervals` and `hazard_label` by hand.

Import scope: this module may import only `src.domain` and `src.events` (30 rule 2). It
imports neither — the schema is self-contained.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HazardLabel = Literal["NONE", "DIRECT", "TOOL", "SURFACE", "BACK_CONTAMINATION"]


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AnnotatedEvent(_Strict):
    """One ground-truth event. `participants` are carrier ids (a zone may be given either
    as `zone_id` or as a participant; matching unions the two)."""

    t_ms: int = Field(ge=0)
    type: str
    participants: list[str]
    zone_id: str | None = None
    ground_truth: Literal[True] = True


class OcclusionInterval(_Strict):
    """A closed interval [t_start, t_end] (ms) during which `carrier_id` was unobservable."""

    carrier_id: str
    t_start: int = Field(ge=0)
    t_end: int = Field(ge=0)

    @model_validator(mode="after")
    def _ordered(self) -> OcclusionInterval:
        if self.t_end < self.t_start:
            raise ValueError(f"occlusion interval for {self.carrier_id}: t_end < t_start")
        return self


class VideoAnnotation(_Strict):
    clip_id: str
    # 20 §Station frame: a calibration change bumps config_version and invalidates fixtures;
    # the scorer warns when a clip's version differs from the loaded station's.
    station_config_version: int | str
    recorded_at: str | None = None
    fps: int | None = Field(default=None, gt=0)
    events: list[AnnotatedEvent] = Field(default_factory=list)
    occlusion_intervals: list[OcclusionInterval] = Field(default_factory=list)
    hazard_label: HazardLabel = "NONE"


def load_annotation(path: Path | str) -> VideoAnnotation:
    """Parse `<clip>.json`; raises `ValueError` (pydantic) on any deviation from the schema."""
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object")
    return VideoAnnotation.model_validate(data)
