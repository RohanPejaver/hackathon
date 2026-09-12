"""20 §Station frame: corner fiducials -> px->mm homography, sub-2 mm on synthetic frames."""

from __future__ import annotations

import math

import pytest

from src.perception.calibration import (
    detect_corners,
    homography_from_corners,
    reprojection_error_mm,
    to_station,
)
from src.perception.config import PerceptionConfig

from .synth import DEFAULT_CORNERS_PX, HEIGHT_MM, WIDTH_MM, mm_to_px, render_frame

EXPECTED_MM = {0: (0.0, 0.0), 1: (WIDTH_MM, 0.0), 2: (WIDTH_MM, HEIGHT_MM), 3: (0.0, HEIGHT_MM)}


def test_corners_detected_on_synthetic_frame(pcfg: PerceptionConfig) -> None:
    frame = render_frame()
    corners = detect_corners(frame, pcfg.marker_dictionary, pcfg.corner_ids)
    assert set(corners) == {0, 1, 2, 3}
    for mid, (x, y) in DEFAULT_CORNERS_PX.items():
        assert math.dist(corners[mid], (x, y)) < 2.0


def test_homography_maps_corners_to_station_frame(pcfg: PerceptionConfig) -> None:
    frame = render_frame()
    corners = detect_corners(frame, pcfg.marker_dictionary, pcfg.corner_ids)
    H = homography_from_corners(corners, pcfg.corner_ids, pcfg.width_mm, pcfg.height_mm)
    assert H.shape == (3, 3)
    for mid, expected in EXPECTED_MM.items():
        assert math.dist(to_station(H, corners[mid]), expected) < 2.0
    assert reprojection_error_mm(H, corners, pcfg.corner_ids, WIDTH_MM, HEIGHT_MM) < 2.0


def test_homography_agrees_with_synth_linear_map(pcfg: PerceptionConfig) -> None:
    frame = render_frame()
    corners = detect_corners(frame, pcfg.marker_dictionary, pcfg.corner_ids)
    H = homography_from_corners(corners, pcfg.corner_ids, pcfg.width_mm, pcfg.height_mm)
    for mm in ((170.0, 470.0), (500.0, 190.0), (870.0, 190.0)):
        px = mm_to_px(mm)
        assert math.dist(to_station(H, (float(px[0]), float(px[1]))), mm) < 3.0


def test_missing_corner_raises(pcfg: PerceptionConfig) -> None:
    three = {k: v for k, v in DEFAULT_CORNERS_PX.items() if k != 2}
    frame = render_frame(corners_px=three)
    corners = detect_corners(frame, pcfg.marker_dictionary, pcfg.corner_ids)
    assert 2 not in corners
    with pytest.raises(ValueError):
        homography_from_corners(corners, pcfg.corner_ids, pcfg.width_mm, pcfg.height_mm)
