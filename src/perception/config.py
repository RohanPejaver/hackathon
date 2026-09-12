"""Perception configuration (31 `perception:` + `temporal:` + station calibration/markers).

Plain values only: the runtime (the composition root) fills this from its loaded YAML via
`PerceptionConfig.build`; perception itself never reads YAML and never imports `src.runtime`
(30 rule 2, rule 4).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerceptionConfig:
    station_id: str
    width_mm: float
    height_mm: float
    # px -> mm 3x3; None = self-calibrate from the four corner markers (20 §Station frame).
    homography: tuple[tuple[float, ...], ...] | None
    fps: int
    t_dwell_ms: int
    t_hysteresis_ms: int
    t_occlusion_max_ms: int
    # Re-observe every visible tracked carrier this often (13 §Epistemic status keeps
    # `last_observed_at` fresh). The runtime sets it to min(t_stale) / 2.
    heartbeat_ms: int
    # Per event type (21 §Grade assignment). GLOVE_CHANGE's observed threshold is > 1.0 by
    # config (EXP-004), so it is always INFERRED.
    threshold_observed: dict[str, float]
    threshold_inferred: dict[str, float]
    camera_source: int | str
    marker_dictionary: str
    # (front-left = origin (0,0), front-right = (W,0), back-right = (W,H), back-left = (0,H))
    corner_ids: tuple[int, int, int, int]
    corner_size_mm: float
    tool_size_mm: float
    hsv_lower: tuple[int, int, int]
    hsv_upper: tuple[int, int, int]
    min_area_px: int
    glove_change_absence_ms: int
    frame_timeout_ms: int
    static_frames: int
    frame_rate_floor_fps: int
    tool_markers: dict[int, str]  # ArUco id -> carrier id (station `markers.tools`)
    surface_markers: dict[int, str]  # ArUco id -> carrier id (station `markers.surfaces`)
    realtime: bool = True  # False: a video file is processed as fast as possible (tests, eval)

    @classmethod
    def build(
        cls,
        *,
        station_id: str,
        width_mm: float,
        height_mm: float,
        homography: tuple[tuple[float, ...], ...] | list[list[float]] | None,
        fps: int,
        t_dwell_ms: int,
        t_hysteresis_ms: int,
        t_occlusion_max_ms: int,
        heartbeat_ms: int,
        threshold_observed: dict[str, float],
        threshold_inferred: dict[str, float],
        camera_source: int | str,
        marker_dictionary: str,
        corner_ids: tuple[int, int, int, int] | list[int],
        corner_size_mm: float,
        tool_size_mm: float,
        hsv_lower: tuple[int, int, int] | list[int],
        hsv_upper: tuple[int, int, int] | list[int],
        min_area_px: int,
        glove_change_absence_ms: int,
        frame_timeout_ms: int,
        static_frames: int,
        frame_rate_floor_fps: int,
        tool_markers: dict[int, str],
        surface_markers: dict[int, str],
        realtime: bool = True,
    ) -> PerceptionConfig:
        """Keyword-only constructor taking plain YAML-shaped values (lists are accepted and
        frozen into tuples so the config is hashable and immutable)."""
        if len(corner_ids) != 4:
            raise ValueError("corner_ids must name exactly four markers")
        h = (
            None
            if homography is None
            else tuple(tuple(float(v) for v in row) for row in homography)
        )
        if h is not None and (len(h) != 3 or any(len(row) != 3 for row in h)):
            raise ValueError("homography must be a 3x3 matrix")
        lo = tuple(int(v) for v in hsv_lower)
        hi = tuple(int(v) for v in hsv_upper)
        if len(lo) != 3 or len(hi) != 3:
            raise ValueError("hsv bounds must have three components")
        ids = tuple(int(v) for v in corner_ids)
        return cls(
            station_id=station_id,
            width_mm=float(width_mm),
            height_mm=float(height_mm),
            homography=h,
            fps=int(fps),
            t_dwell_ms=int(t_dwell_ms),
            t_hysteresis_ms=int(t_hysteresis_ms),
            t_occlusion_max_ms=int(t_occlusion_max_ms),
            heartbeat_ms=int(heartbeat_ms),
            threshold_observed=dict(threshold_observed),
            threshold_inferred=dict(threshold_inferred),
            camera_source=camera_source,
            marker_dictionary=marker_dictionary,
            corner_ids=(ids[0], ids[1], ids[2], ids[3]),
            corner_size_mm=float(corner_size_mm),
            tool_size_mm=float(tool_size_mm),
            hsv_lower=(lo[0], lo[1], lo[2]),
            hsv_upper=(hi[0], hi[1], hi[2]),
            min_area_px=int(min_area_px),
            glove_change_absence_ms=int(glove_change_absence_ms),
            frame_timeout_ms=int(frame_timeout_ms),
            static_frames=int(static_frames),
            frame_rate_floor_fps=int(frame_rate_floor_fps),
            tool_markers={int(k): str(v) for k, v in tool_markers.items()},
            surface_markers={int(k): str(v) for k, v in surface_markers.items()},
            realtime=realtime,
        )

    def thresholds_for(self, event_type: str) -> tuple[float, float]:
        """(observed, inferred) thresholds; a type missing from both maps gets (0.85, 0.60)."""
        observed = self.threshold_observed.get(event_type, 0.85)
        inferred = self.threshold_inferred.get(event_type, 0.60)
        return observed, inferred
