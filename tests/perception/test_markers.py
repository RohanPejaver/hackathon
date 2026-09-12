"""39 §3: ArUco tags give guaranteed tool/surface identity."""

from __future__ import annotations

import math

from src.perception.config import PerceptionConfig
from src.perception.markers import detect_markers

from .synth import DEFAULT_CORNERS_PX, render_frame


def test_marker_ids_and_centres(pcfg: PerceptionConfig) -> None:
    placed = {10: (550, 585), 20: (400, 300), 11: (900, 200)}
    frame = render_frame(markers_px=placed)
    found = detect_markers(frame, pcfg.marker_dictionary)
    ids = [m.id for m in found]
    assert ids == sorted(ids)
    assert set(ids) == set(DEFAULT_CORNERS_PX) | set(placed)
    by_id = {m.id: m for m in found}
    for mid, centre in {**DEFAULT_CORNERS_PX, **placed}.items():
        assert math.dist(by_id[mid].centre_px, centre) < 3.0
        assert len(by_id[mid].corners_px) == 4


def test_no_markers_on_blank_frame(pcfg: PerceptionConfig) -> None:
    frame = render_frame(corners_px={})
    assert detect_markers(frame, pcfg.marker_dictionary) == []
