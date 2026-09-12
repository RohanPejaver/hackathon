"""Detections -> stable carrier tracks in the station frame, plus the honesty events (21
§Obligations of honesty, 23 P3/P4).

Failing to report an occlusion is a more serious defect than a false detection — that
sentence is the contract. Nothing here suppresses an observation because it looks
implausible; plausibility belongs to the reasoning layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from src.domain import CarrierKind, StationConfig

from .calibration import local_scale_mm_per_px, to_station
from .config import PerceptionConfig
from .markers import Marker
from .segment import Blob

Pt = tuple[float, float]

GLOVE_MIN_RADIUS_MM = 40.0
SURFACE_RADIUS_MM = 120.0
SUSPECT_RADIUS_MM = 150.0
WORKER_SLOT = 0


@dataclass(frozen=True)
class Track:
    carrier_id: str
    kind: CarrierKind
    contact_point_mm: Pt | None
    radius_mm: float
    visible: bool  # seen in the current frame
    last_seen_ms: int | None
    marker_id: int | None
    # Compatible extension: detector confidence of the current observation (glove blob
    # confidence; 1.0 for a marker). The assembler grades glove-derived events with it.
    confidence: float = 1.0


@dataclass
class _State:
    carrier_id: str
    kind: CarrierKind
    marker_id: int | None
    radius_mm: float
    pos_mm: Pt | None = None
    last_seen_ms: int | None = None
    seen_now: bool = False
    confidence: float = 1.0
    reported_unknown: bool = False  # CARRIER_OBSERVABILITY_CHANGED -> UNKNOWN already sent
    last_heartbeat_ms: int | None = None
    flagged_pairs: set[str] = field(default_factory=set)


class Tracker:
    """Identity comes from marker ids (tools, surfaces) and from the single HSV glove blob.

    CONTRACT-GAP: zone-fixed carriers (a station carrier with a home_zone and no marker —
    bins, the landing) are not visually tracked; their region is their zone polygon and the
    assembler reaches them through zone events. They receive no observability events from
    here, so their epistemic status stays whatever the reducer derives from zone contact.
    """

    def __init__(self, cfg: PerceptionConfig, station: StationConfig) -> None:
        self._cfg = cfg
        self._states: dict[str, _State] = {}
        gloves = [c for c in station.carriers.values() if c.kind == CarrierKind.GLOVES]
        self._glove_id: str | None = gloves[0].carrier_id if gloves else None
        if self._glove_id is not None:
            self._states[self._glove_id] = _State(
                self._glove_id, CarrierKind.GLOVES, None, GLOVE_MIN_RADIUS_MM
            )
        for mid, cid in cfg.tool_markers.items():
            self._states[cid] = _State(cid, CarrierKind.TOOL, mid, cfg.tool_size_mm * 2.0)
        for mid, cid in cfg.surface_markers.items():
            self._states[cid] = _State(cid, CarrierKind.SURFACE, mid, SURFACE_RADIUS_MM)
        self._by_marker: dict[int, str] = {**cfg.tool_markers, **cfg.surface_markers}

    @property
    def glove_id(self) -> str | None:
        return self._glove_id

    # ---- drafts ----------------------------------------------------------------------------
    @staticmethod
    def _observability(carrier: str, epistemic: str, cause: str, t_ms: int) -> dict[str, object]:
        return {
            "type": "CARRIER_OBSERVABILITY_CHANGED",
            "t_occurred": t_ms,
            "source": "PERCEPTION",
            "confidence": 1.0,
            "evidence": {"track_ids": [carrier], "zone_ids": []},
            "carrier": carrier,
            "epistemic": epistemic,
            "cause": cause,
        }

    @staticmethod
    def _suspect(a: str, b: str, cause: str, t_ms: int) -> dict[str, object]:
        first, second = sorted((a, b))
        return {
            "type": "TRACK_IDENTITY_SUSPECT",
            "t_occurred": t_ms,
            "source": "PERCEPTION",
            "confidence": 1.0,
            "evidence": {"track_ids": [first, second], "zone_ids": []},
            "a": first,
            "b": second,
            "cause": cause,
        }

    # ---- update ----------------------------------------------------------------------------
    def update(
        self,
        t_ms: int,
        glove: Blob | None,
        markers: list[Marker],
        H: NDArray[np.float64],
    ) -> tuple[dict[str, Track], list[dict[str, object]]]:
        drafts: list[dict[str, object]] = []
        for s in self._states.values():
            s.seen_now = False

        # detections -> states
        if glove is not None and self._glove_id is not None:
            s = self._states[self._glove_id]
            centre = to_station(H, glove.centroid_px)
            scale = local_scale_mm_per_px(H, glove.centroid_px)
            radius = max(GLOVE_MIN_RADIUS_MM, math.sqrt(glove.area_px) / 2.0 * scale)
            self._observe(s, centre, radius, glove.confidence, t_ms, drafts)

        unknown_detections: list[Pt] = []
        for m in markers:
            cid = self._by_marker.get(m.id)
            if cid is None:
                if m.id in self._cfg.corner_ids:
                    continue
                unknown_detections.append(to_station(H, m.centre_px))
                continue
            s = self._states[cid]
            self._observe(s, to_station(H, m.centre_px), s.radius_mm, 1.0, t_ms, drafts)

        # occlusion ladder (21): unseen >= t_occlusion_max -> UNKNOWN, once per outage
        for s in self._states.values():
            if s.seen_now or s.last_seen_ms is None or s.reported_unknown:
                continue
            gap = t_ms - s.last_seen_ms
            if gap >= self._cfg.t_occlusion_max_ms:
                s.reported_unknown = True
                drafts.append(
                    self._observability(s.carrier_id, "UNKNOWN", f"occluded {gap} ms", t_ms)
                )

        # identity suspicion (23 P3): an unlabelled detection reappears where two lost
        # carriers of the same kind were last seen -> never silently reassign
        if unknown_detections:
            drafts += self._suspects(unknown_detections, t_ms)

        tracks = {
            s.carrier_id: Track(
                carrier_id=s.carrier_id,
                kind=s.kind,
                contact_point_mm=s.pos_mm,
                radius_mm=s.radius_mm,
                visible=s.seen_now,
                last_seen_ms=s.last_seen_ms,
                marker_id=s.marker_id,
                confidence=s.confidence if s.seen_now else 0.0,
            )
            for s in self._states.values()
        }
        return tracks, drafts

    def _observe(
        self,
        s: _State,
        pos: Pt,
        radius: float,
        confidence: float,
        t_ms: int,
        drafts: list[dict[str, object]],
    ) -> None:
        if s.reported_unknown:
            drafts.append(self._observability(s.carrier_id, "TRACKED", "re-observed", t_ms))
            s.reported_unknown = False
            s.last_heartbeat_ms = t_ms
            s.flagged_pairs.clear()
        elif s.last_seen_ms is None:
            drafts.append(self._observability(s.carrier_id, "TRACKED", "first observed", t_ms))
            s.last_heartbeat_ms = t_ms
        elif s.last_heartbeat_ms is None or t_ms - s.last_heartbeat_ms >= self._cfg.heartbeat_ms:
            drafts.append(self._observability(s.carrier_id, "TRACKED", "heartbeat", t_ms))
            s.last_heartbeat_ms = t_ms
        s.pos_mm = pos
        s.radius_mm = radius
        s.confidence = confidence
        s.last_seen_ms = t_ms
        s.seen_now = True

    def _suspects(self, detections: list[Pt], t_ms: int) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        lost = [
            s
            for s in self._states.values()
            if not s.seen_now and s.pos_mm is not None and s.last_seen_ms is not None
        ]
        for i, a in enumerate(lost):
            for b in lost[i + 1 :]:
                if a.kind != b.kind or a.pos_mm is None or b.pos_mm is None:
                    continue
                if b.carrier_id in a.flagged_pairs:
                    continue
                for p in detections:
                    if (
                        math.dist(p, a.pos_mm) <= SUSPECT_RADIUS_MM
                        and math.dist(p, b.pos_mm) <= SUSPECT_RADIUS_MM
                    ):
                        a.flagged_pairs.add(b.carrier_id)
                        b.flagged_pairs.add(a.carrier_id)
                        out.append(
                            self._suspect(
                                a.carrier_id,
                                b.carrier_id,
                                "unlabelled detection reappeared within "
                                f"{SUSPECT_RADIUS_MM:.0f} mm of both last positions",
                                t_ms,
                            )
                        )
                        break
        return out
