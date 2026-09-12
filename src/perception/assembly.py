"""Tracks -> discrete semantic events with dwell, hysteresis and episode collapsing (10 layer
4; 12 §Contact events; 20 §Contact predicate). Ten seconds of continuous contact is ONE
episode — solved here, not at the alert layer (16).

Payloads are plain dicts missing only the envelope the pipeline adds (`event_id`,
`station_id`, `grade`, `evidence.frame_range`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from src.domain import CarrierKind, StationConfig, ZoneKind

from .config import PerceptionConfig
from .tracker import WORKER_SLOT, Track

Pt = tuple[float, float]

ENTRY_KINDS = frozenset(
    {
        ZoneKind.INGREDIENT,
        ZoneKind.GLOVE_DISPENSER,
        ZoneKind.CLEAN_STOCK,
        ZoneKind.TOOL_RACK,
        ZoneKind.WASH,
    }
)
CONTACT_KINDS = frozenset({ZoneKind.WORK, ZoneKind.LANDING})
GLOVE_CHANGE_CONFIDENCE = 0.7
SWAP_CONFIDENCE = 0.95


@dataclass
class _Episode:
    inside_since: int | None = None
    active: bool = False
    began_at: int = 0
    last_inside_ms: int = 0
    outside_since: int | None = None
    confidence: float = 1.0
    point: Pt = (0.0, 0.0)


@dataclass
class _Zone:
    zone_id: str
    kind: ZoneKind
    bound_carrier: str | None
    contour: NDArray[np.float32]


class Assembler:
    def __init__(self, cfg: PerceptionConfig, station: StationConfig) -> None:
        self._cfg = cfg
        self._zones: list[_Zone] = [
            _Zone(
                z.zone_id,
                z.kind,
                z.bound_carrier,
                np.array([[p.x, p.y] for p in z.polygon], dtype=np.float32).reshape(-1, 1, 2),
            )
            for z in station.zones.values()
            if len(z.polygon) >= 3
        ]
        self._zone_kind = {z.zone_id: z.kind for z in self._zones}
        self._episodes: dict[tuple[str, str], _Episode] = {}  # (carrier, zone) / (a, b)
        gloves = [c for c in station.carriers.values() if c.kind == CarrierKind.GLOVES]
        self._glove_id: str | None = gloves[0].carrier_id if gloves else None
        # swaps (39 §3): the active set per kind starts from the station carriers
        self._active: dict[CarrierKind, set[str]] = {
            CarrierKind.TOOL: {
                c.carrier_id for c in station.carriers.values() if c.kind == CarrierKind.TOOL
            },
            CarrierKind.SURFACE: {
                c.carrier_id for c in station.carriers.values() if c.kind == CarrierKind.SURFACE
            },
        }
        self._last_glove_contact: dict[str, int] = {}
        self._from_clean_stock: dict[str, str] = {}  # candidate carrier -> clean-stock zone
        self._outside_stock_since: dict[str, int | None] = {}
        # glove change (39 §3, EXP-004)
        self._dispenser_pending = False
        self._glove_absent_since: int | None = None

    # ---- helpers ---------------------------------------------------------------------------
    def _inside(self, z: _Zone, p: Pt) -> bool:
        return float(cv2.pointPolygonTest(z.contour, (float(p[0]), float(p[1])), False)) >= 0.0

    def _zone_kind_of(self, zone_id: str) -> ZoneKind | None:
        return self._zone_kind.get(zone_id)

    def _event(
        self,
        kind: str,
        t_ms: int,
        confidence: float,
        track_ids: list[str],
        zone_ids: list[str],
        **fields: object,
    ) -> dict[str, object]:
        return {
            "type": kind,
            "t_occurred": t_ms,
            "source": "PERCEPTION",
            "confidence": confidence,
            "evidence": {"track_ids": track_ids, "zone_ids": zone_ids},
            **fields,
        }

    # ---- episode machine ---------------------------------------------------------------------
    def _drive(
        self,
        key: tuple[str, str],
        inside: bool,
        t_ms: int,
        confidence: float,
        point: Pt,
    ) -> tuple[bool, bool, _Episode]:
        """Returns (begin_fired, end_fired, episode)."""
        ep = self._episodes.setdefault(key, _Episode())
        if inside:
            ep.outside_since = None
            ep.last_inside_ms = t_ms
            if ep.inside_since is None:
                ep.inside_since = t_ms
            if not ep.active and t_ms - ep.inside_since >= self._cfg.t_dwell_ms:
                ep.active = True
                ep.began_at = t_ms
                ep.confidence = confidence
                ep.point = point
                return True, False, ep
            return False, False, ep
        ep.inside_since = None
        if ep.active:
            if ep.outside_since is None:
                ep.outside_since = t_ms
            elif t_ms - ep.outside_since >= self._cfg.t_hysteresis_ms:
                ep.active = False
                ep.outside_since = None
                return False, True, ep
        return False, False, ep

    # ---- step ----------------------------------------------------------------------------------
    def step(self, t_ms: int, tracks: dict[str, Track]) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        visible = {
            cid: t for cid, t in tracks.items() if t.visible and t.contact_point_mm is not None
        }

        # zone membership: every zone the contact point falls in (zones may overlap, 20)
        in_zone: dict[tuple[str, str], bool] = {}
        for cid, tr in visible.items():
            assert tr.contact_point_mm is not None
            for z in self._zones:
                if z.bound_carrier == cid:
                    continue  # a carrier is never in contact with itself
                in_zone[(cid, z.zone_id)] = self._inside(z, tr.contact_point_mm)
        for key in list(self._episodes):
            cid, other = key
            if other in self._zone_kind and key not in in_zone:
                in_zone[key] = False  # not visible -> not inside
        for (cid, zone_id), inside in in_zone.items():
            trk = tracks.get(cid)
            conf = trk.confidence if trk is not None and trk.visible else 0.0
            pt = trk.contact_point_mm if trk is not None and trk.contact_point_mm else (0.0, 0.0)
            began, ended, ep = self._drive((cid, zone_id), inside, t_ms, conf, pt)
            kind = self._zone_kind_of(zone_id)
            if began:
                if kind in CONTACT_KINDS:
                    # CONTRACT-GAP: b is a zone id; the reducer resolves it to the bound
                    # carrier (and for LANDING to the food on it).
                    out.append(
                        self._event(
                            "CONTACT_BEGIN",
                            t_ms,
                            ep.confidence,
                            [cid],
                            [zone_id],
                            a=cid,
                            b=zone_id,
                            contact_point={"x": ep.point[0], "y": ep.point[1]},
                        )
                    )
                    self._on_begin(cid, zone_id, t_ms, is_zone=True)
                else:
                    out.append(
                        self._event(
                            "ZONE_ENTRY",
                            t_ms,
                            ep.confidence,
                            [cid],
                            [zone_id],
                            carrier=cid,
                            zone=zone_id,
                            depth=1.0,
                        )
                    )
                    self._on_begin(cid, zone_id, t_ms, is_zone=True)
            elif ended:
                duration = max(0, ep.last_inside_ms - ep.began_at)
                if kind in CONTACT_KINDS:
                    out.append(
                        self._event(
                            "CONTACT_END",
                            t_ms,
                            ep.confidence,
                            [cid],
                            [zone_id],
                            a=cid,
                            b=zone_id,
                            duration_ms=duration,
                        )
                    )
                else:
                    out.append(
                        self._event(
                            "ZONE_EXIT",
                            t_ms,
                            ep.confidence,
                            [cid],
                            [zone_id],
                            carrier=cid,
                            zone=zone_id,
                            dwell_ms=duration,
                        )
                    )

        # carrier <-> carrier contact: circles overlap for >= t_dwell (20 §Contact predicate)
        overlap: dict[tuple[str, str], tuple[bool, float, Pt]] = {}
        ids = sorted(visible)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                ta, tb = visible[a], visible[b]
                if ta.kind == tb.kind:
                    continue  # gloves<->tool, tool<->surface, gloves<->surface only
                assert ta.contact_point_mm is not None and tb.contact_point_mm is not None
                d = math.dist(ta.contact_point_mm, tb.contact_point_mm)
                mid = (
                    (ta.contact_point_mm[0] + tb.contact_point_mm[0]) / 2.0,
                    (ta.contact_point_mm[1] + tb.contact_point_mm[1]) / 2.0,
                )
                overlap[(a, b)] = (
                    d <= ta.radius_mm + tb.radius_mm,
                    min(ta.confidence, tb.confidence),
                    mid,
                )
        for key in list(self._episodes):
            if key[1] not in self._zone_kind and key not in overlap:
                overlap[key] = (False, 0.0, (0.0, 0.0))
        for (a, b), (touching, conf, mid) in overlap.items():
            began, ended, ep = self._drive((a, b), touching, t_ms, conf, mid)
            if began:
                out.append(
                    self._event(
                        "CONTACT_BEGIN",
                        t_ms,
                        ep.confidence,
                        [a, b],
                        [],
                        a=a,
                        b=b,
                        contact_point={"x": ep.point[0], "y": ep.point[1]},
                    )
                )
                self._on_begin(a, b, t_ms, is_zone=False)
            elif ended:
                out.append(
                    self._event(
                        "CONTACT_END",
                        t_ms,
                        ep.confidence,
                        [a, b],
                        [],
                        a=a,
                        b=b,
                        duration_ms=max(0, ep.last_inside_ms - ep.began_at),
                    )
                )

        out += self._glove_change(t_ms, tracks)
        out += self._swaps(t_ms, tracks)
        return out

    # ---- bookkeeping for resets ------------------------------------------------------------
    def _on_begin(self, a: str, b: str, t_ms: int, *, is_zone: bool) -> None:
        """Record glove contacts (for swap retirement) and glove-change intent."""
        if self._glove_id is None:
            return
        if is_zone:
            if a == self._glove_id:
                kind = self._zone_kind_of(b)
                if kind == ZoneKind.GLOVE_DISPENSER:
                    self._dispenser_pending = True
                else:
                    self._dispenser_pending = False
                    bound = next((z.bound_carrier for z in self._zones if z.zone_id == b), None)
                    if bound is not None:
                        self._last_glove_contact[bound] = t_ms
            return
        if self._glove_id in (a, b):
            other = b if a == self._glove_id else a
            self._last_glove_contact[other] = t_ms
            self._dispenser_pending = False

    def _glove_change(self, t_ms: int, tracks: dict[str, Track]) -> list[dict[str, object]]:
        """ZONE_ENTRY(glove_dispenser), then the blob absent >= glove_change_absence_ms, then
        it reappears -> GLOVE_CHANGE(DON) at 0.7 (INFERRED by config; EXP-004). No DOFF."""
        if self._glove_id is None:
            return []
        tr = tracks.get(self._glove_id)
        present = tr is not None and tr.visible
        if not present:
            if self._glove_absent_since is None:
                self._glove_absent_since = t_ms
            return []
        absent_since = self._glove_absent_since
        self._glove_absent_since = None
        if (
            self._dispenser_pending
            and absent_since is not None
            and t_ms - absent_since >= self._cfg.glove_change_absence_ms
        ):
            self._dispenser_pending = False
            return [
                self._event(
                    "GLOVE_CHANGE",
                    t_ms,
                    GLOVE_CHANGE_CONFIDENCE,
                    [self._glove_id],
                    [z.zone_id for z in self._zones if z.kind == ZoneKind.GLOVE_DISPENSER],
                    worker_slot=WORKER_SLOT,
                    phase="DON",
                )
            ]
        return []

    def _swaps(self, t_ms: int, tracks: dict[str, Track]) -> list[dict[str, object]]:
        """A marker-bearing carrier outside the active set first seen (dwell satisfied)
        inside CLEAN_STOCK, later seen outside it for >= t_dwell -> TOOL_SWAP / SURFACE_SWAP."""
        out: list[dict[str, object]] = []
        for cid, tr in tracks.items():
            if tr.marker_id is None or tr.kind not in self._active:
                continue
            if cid in self._active[tr.kind]:
                continue
            if not tr.visible or tr.contact_point_mm is None:
                self._outside_stock_since[cid] = None
                continue
            stock_zones = [
                z
                for z in self._zones
                if z.kind == ZoneKind.CLEAN_STOCK and self._inside(z, tr.contact_point_mm)
            ]
            if stock_zones:
                self._outside_stock_since[cid] = None
                ep = self._episodes.get((cid, stock_zones[0].zone_id))
                if ep is not None and ep.active:
                    self._from_clean_stock[cid] = stock_zones[0].zone_id
                continue
            from_zone = self._from_clean_stock.get(cid)
            if from_zone is None:
                continue
            since = self._outside_stock_since.get(cid)
            if since is None:
                self._outside_stock_since[cid] = t_ms
                continue
            if t_ms - since < self._cfg.t_dwell_ms:
                continue
            retired = self._retire_candidate(tr.kind)
            if retired is None:
                continue  # nothing to retire; the introduction is recorded by zone events
            self._active[tr.kind].discard(retired)
            self._active[tr.kind].add(cid)
            del self._from_clean_stock[cid]
            self._outside_stock_since[cid] = None
            out.append(
                self._event(
                    "TOOL_SWAP" if tr.kind == CarrierKind.TOOL else "SURFACE_SWAP",
                    t_ms,
                    SWAP_CONFIDENCE,
                    [retired, cid],
                    [from_zone],
                    retired=retired,
                    introduced=cid,
                    from_zone=from_zone,
                )
            )
        return out

    def _retire_candidate(self, kind: CarrierKind) -> str | None:
        active = self._active[kind]
        touched = [
            (self._last_glove_contact[c], c) for c in active if c in self._last_glove_contact
        ]
        if touched:
            return max(touched)[1]
        if len(active) == 1:
            return next(iter(active))
        return None
