"""ArUco marker detection (39 §3): guaranteed identity for tools, swappable surfaces and the
four station-corner fiducials. Deterministic; no learned model."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

Pt = tuple[float, float]


@dataclass(frozen=True)
class Marker:
    id: int
    corners_px: tuple[Pt, Pt, Pt, Pt]
    centre_px: Pt


_DETECTORS: dict[str, cv2.aruco.ArucoDetector] = {}


def _detector(dictionary: str) -> cv2.aruco.ArucoDetector:
    det = _DETECTORS.get(dictionary)
    if det is None:
        if not hasattr(cv2.aruco, dictionary):
            raise ValueError(f"unknown ArUco dictionary {dictionary!r}")
        predefined = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary))
        det = cv2.aruco.ArucoDetector(predefined, cv2.aruco.DetectorParameters())
        _DETECTORS[dictionary] = det
    return det


def detect_markers(frame_bgr: NDArray[np.uint8], dictionary: str) -> list[Marker]:
    """All markers of the named predefined dictionary visible in the frame, sorted by id."""
    corners, ids, _rejected = _detector(dictionary).detectMarkers(frame_bgr)
    if ids is None or len(ids) == 0:
        return []
    out: list[Marker] = []
    for quad, mid in zip(corners, np.asarray(ids).ravel(), strict=True):
        pts = np.asarray(quad, dtype=np.float64).reshape(4, 2)
        c = pts.mean(axis=0)
        out.append(
            Marker(
                id=int(mid),
                corners_px=(
                    (float(pts[0, 0]), float(pts[0, 1])),
                    (float(pts[1, 0]), float(pts[1, 1])),
                    (float(pts[2, 0]), float(pts[2, 1])),
                    (float(pts[3, 0]), float(pts[3, 1])),
                ),
                centre_px=(float(c[0]), float(c[1])),
            )
        )
    out.sort(key=lambda m: m.id)
    return out
