"""HSV colour segmentation of the gloved hand (39 §3): nitrile gloves are strongly saturated
against a white/steel surface. Deterministic, ~2 ms/frame, no training data."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Blob:
    centroid_px: tuple[float, float]
    area_px: float
    bbox: tuple[int, int, int, int]  # x, y, w, h
    confidence: float


def blob_confidence(area_px: float, min_area_px: int) -> float:
    """0.5 at the detection floor rising to 1.0 at four times `min_area_px`: a marginal blob
    is ~0.62 (INFERRED at the 0.60 threshold), a solid glove 1.0 (OBSERVED at 0.85)."""
    return min(1.0, 0.5 + 0.5 * min(1.0, area_px / (4.0 * float(min_area_px))))


def glove_mask(
    frame_bgr: NDArray[np.uint8],
    hsv_lower: tuple[int, int, int],
    hsv_upper: tuple[int, int, int],
) -> NDArray[np.uint8]:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    lo = np.array(hsv_lower, dtype=np.uint8)
    hi = np.array(hsv_upper, dtype=np.uint8)
    mask = cv2.inRange(hsv, lo, hi)
    return np.asarray(mask, dtype=np.uint8)


def glove_blob(
    frame_bgr: NDArray[np.uint8],
    hsv_lower: tuple[int, int, int],
    hsv_upper: tuple[int, int, int],
    min_area_px: int,
) -> Blob | None:
    """Largest HSV-in-range contour with area >= `min_area_px`, or None."""
    mask = glove_mask(frame_bgr, hsv_lower, hsv_upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best: NDArray[np.int32] | None = None
    best_area = 0.0
    for c in contours:
        area = float(cv2.contourArea(c))
        if area > best_area:
            best_area = area
            best = np.asarray(c, dtype=np.int32)
    if best is None or best_area < float(min_area_px):
        return None
    m = cv2.moments(best)
    if m["m00"] <= 0.0:
        return None
    cx = float(m["m10"] / m["m00"])
    cy = float(m["m01"] / m["m00"])
    x, y, w, h = cv2.boundingRect(best)
    return Blob(
        centroid_px=(cx, cy),
        area_px=best_area,
        bbox=(int(x), int(y), int(w), int(h)),
        confidence=blob_confidence(best_area, min_area_px),
    )
