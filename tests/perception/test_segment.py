"""39 §3: HSV segmentation of the glove; confidence from blob area (21 §Grade assignment)."""

from __future__ import annotations

import math

from src.perception.config import PerceptionConfig
from src.perception.segment import glove_blob

from .synth import render_frame

MARGINAL_RADIUS_PX = 24  # contour area ~1.15-1.2 x min_area_px (1500)


def test_blob_centroid_matches_drawn_circle(pcfg: PerceptionConfig) -> None:
    frame = render_frame(glove_px=(640, 360), glove_radius_px=60)
    blob = glove_blob(frame, pcfg.hsv_lower, pcfg.hsv_upper, pcfg.min_area_px)
    assert blob is not None
    assert math.dist(blob.centroid_px, (640, 360)) < 3.0
    assert blob.confidence == 1.0
    x, y, w, h = blob.bbox
    assert x <= 640 <= x + w and y <= 360 <= y + h


def test_small_circle_is_not_a_glove(pcfg: PerceptionConfig) -> None:
    frame = render_frame(glove_px=(640, 360), glove_radius_px=10)
    assert glove_blob(frame, pcfg.hsv_lower, pcfg.hsv_upper, pcfg.min_area_px) is None


def test_no_glove_no_blob(pcfg: PerceptionConfig) -> None:
    assert glove_blob(render_frame(), pcfg.hsv_lower, pcfg.hsv_upper, pcfg.min_area_px) is None


def test_marginal_blob_confidence_is_inferred_band(pcfg: PerceptionConfig) -> None:
    frame = render_frame(glove_px=(640, 360), glove_radius_px=MARGINAL_RADIUS_PX)
    blob = glove_blob(frame, pcfg.hsv_lower, pcfg.hsv_upper, pcfg.min_area_px)
    assert blob is not None
    assert pcfg.min_area_px <= blob.area_px <= 1.3 * pcfg.min_area_px
    assert 0.6 <= blob.confidence < 0.7
