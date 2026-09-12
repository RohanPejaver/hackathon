"""Station frame (20 §Station frame): four ArUco corner markers -> px->mm homography.

Corner ids are ordered (front-left = origin (0,0), front-right = (W,0), back-right = (W,H),
back-left = (0,H)). Everything downstream reasons in millimetres; pixels never leave this
module except as the input to `to_station`.
"""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np
from numpy.typing import NDArray

from .markers import detect_markers

Pt = tuple[float, float]


def detect_corners(
    frame_bgr: NDArray[np.uint8], dictionary: str, corner_ids: Sequence[int]
) -> dict[int, Pt]:
    """Marker id -> centre (px) for the corner ids that are present in the frame."""
    wanted = set(int(i) for i in corner_ids)
    return {m.id: m.centre_px for m in detect_markers(frame_bgr, dictionary) if m.id in wanted}


def station_corners_mm(width_mm: float, height_mm: float) -> tuple[Pt, Pt, Pt, Pt]:
    return ((0.0, 0.0), (width_mm, 0.0), (width_mm, height_mm), (0.0, height_mm))


def homography_from_corners(
    corners: dict[int, Pt], corner_ids: Sequence[int], width_mm: float, height_mm: float
) -> NDArray[np.float64]:
    """3x3 px->mm homography. Raises ValueError unless all four corner ids are present."""
    ids = [int(i) for i in corner_ids]
    if len(ids) != 4:
        raise ValueError("corner_ids must name exactly four markers")
    missing = [i for i in ids if i not in corners]
    if missing:
        raise ValueError(f"corner markers missing: {missing}")
    src = np.array([corners[i] for i in ids], dtype=np.float32)
    dst = np.array(station_corners_mm(width_mm, height_mm), dtype=np.float32)
    h = cv2.getPerspectiveTransform(src, dst)
    out = np.asarray(h, dtype=np.float64)
    if out.shape != (3, 3) or not np.all(np.isfinite(out)):
        raise ValueError("degenerate corner configuration")
    return out


def to_station(H: NDArray[np.float64], xy_px: Pt) -> Pt:
    """Map a pixel point into the station frame (mm)."""
    v = H @ np.array([xy_px[0], xy_px[1], 1.0], dtype=np.float64)
    w = float(v[2])
    if w == 0.0:
        raise ValueError("point at infinity under the calibration homography")
    return (float(v[0]) / w, float(v[1]) / w)


def local_scale_mm_per_px(H: NDArray[np.float64], xy_px: Pt) -> float:
    """Millimetres per pixel around a point (mean of the two axis derivatives)."""
    x, y = xy_px
    p0 = to_station(H, (x, y))
    px = to_station(H, (x + 1.0, y))
    py = to_station(H, (x, y + 1.0))
    sx = float(np.hypot(px[0] - p0[0], px[1] - p0[1]))
    sy = float(np.hypot(py[0] - p0[0], py[1] - p0[1]))
    return (sx + sy) / 2.0


def reprojection_error_mm(
    H: NDArray[np.float64],
    corners: dict[int, Pt],
    corner_ids: Sequence[int],
    width_mm: float,
    height_mm: float,
) -> float:
    """Max distance (mm) between each detected corner mapped through H and its nominal
    station position. Corner ids absent from `corners` are skipped."""
    worst = 0.0
    for cid, nominal in zip(corner_ids, station_corners_mm(width_mm, height_mm), strict=True):
        if int(cid) not in corners:
            continue
        mx, my = to_station(H, corners[int(cid)])
        worst = max(worst, float(np.hypot(mx - nominal[0], my - nominal[1])))
    return worst
