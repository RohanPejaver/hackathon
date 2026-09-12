"""21 §Obligations of honesty / 23 P3-P4, driven through the real pipeline on synthetic
frames: occlusion -> UNKNOWN once, re-observation -> TRACKED once, heartbeats, identity
suspicion when an unlabelled detection reappears where two lost carriers were."""

from __future__ import annotations

from src.domain import StationConfig
from src.perception.config import PerceptionConfig
from src.perception.pipeline import PerceptionPipeline

from .conftest import FRAME_MS
from .synth import mm_to_px, render_frame

GLOVE_MM = (170.0, 470.0)  # bin:pesto
TOOL_MM = (500.0, 40.0)  # outside every zone
TOOL2_MM = (560.0, 40.0)


def _pipeline(pcfg: PerceptionConfig, station: StationConfig) -> PerceptionPipeline:
    p = PerceptionPipeline()
    p.configure(pcfg, station)
    return p


def _obs(events: list[dict[str, object]], carrier: str) -> list[tuple[str, str]]:
    return [
        (str(e["epistemic"]), str(e["cause"]))
        for e in events
        if e["type"] == "CARRIER_OBSERVABILITY_CHANGED" and e["carrier"] == carrier
    ]


def test_glove_occlusion_reported_once_and_reobserved_once(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = _pipeline(pcfg, station)
    events: list[dict[str, object]] = []
    i = 0
    for _ in range(10):
        events += p.process_frame(render_frame(glove_px=mm_to_px(GLOVE_MM)), i * FRAME_MS)
        i += 1
    assert _obs(events, "gloves") == [("TRACKED", "first observed")]
    events = []
    for _ in range(50):  # 3.3 s absent
        events += p.process_frame(render_frame(), i * FRAME_MS)
        i += 1
    obs = _obs(events, "gloves")
    assert len(obs) == 1 and obs[0][0] == "UNKNOWN" and obs[0][1].startswith("occluded ")
    events = []
    for _ in range(5):
        events += p.process_frame(render_frame(glove_px=mm_to_px(GLOVE_MM)), i * FRAME_MS)
        i += 1
    assert _obs(events, "gloves") == [("TRACKED", "re-observed")]


def test_short_occlusion_is_silent(pcfg: PerceptionConfig, station: StationConfig) -> None:
    p = _pipeline(pcfg, station)
    events: list[dict[str, object]] = []
    i = 0
    for _ in range(5):
        events += p.process_frame(render_frame(glove_px=mm_to_px(GLOVE_MM)), i * FRAME_MS)
        i += 1
    events = []
    for _ in range(20):  # 1.3 s < t_occlusion_max
        events += p.process_frame(render_frame(), i * FRAME_MS)
        i += 1
    for _ in range(5):
        events += p.process_frame(render_frame(glove_px=mm_to_px(GLOVE_MM)), i * FRAME_MS)
        i += 1
    assert _obs(events, "gloves") == []


def test_heartbeat_for_a_continuously_visible_tool(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = _pipeline(pcfg, station)
    events: list[tuple[int, dict[str, object]]] = []
    for i in range(int(9000 / FRAME_MS) + 1):  # 9 s
        t = i * FRAME_MS
        for e in p.process_frame(render_frame(markers_px={10: mm_to_px(TOOL_MM)}), t):
            events.append((t, e))
    beats = [
        t
        for t, e in events
        if e["type"] == "CARRIER_OBSERVABILITY_CHANGED"
        and e["carrier"] == "spreader"
        and e["cause"] == "heartbeat"
    ]
    assert len(beats) == 1
    assert 8000 <= beats[0] <= 8000 + 2 * FRAME_MS
    assert all(e["epistemic"] == "TRACKED" for _, e in events if e["cause"] == "heartbeat")


def test_identity_suspect_when_unlabelled_detection_reappears_between_two_lost_tools(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = _pipeline(pcfg, station)
    i = 0
    events: list[dict[str, object]] = []
    both = {10: mm_to_px(TOOL_MM), 11: mm_to_px(TOOL2_MM)}
    for _ in range(5):
        events += p.process_frame(render_frame(markers_px=both), i * FRAME_MS)
        i += 1
    for _ in range(5):  # both vanish
        events += p.process_frame(render_frame(), i * FRAME_MS)
        i += 1
    mid = ((TOOL_MM[0] + TOOL2_MM[0]) / 2, TOOL_MM[1])
    for _ in range(5):  # an unknown marker (id 30, in no map) reappears equidistant
        events += p.process_frame(render_frame(markers_px={30: mm_to_px(mid)}), i * FRAME_MS)
        i += 1
    suspects = [e for e in events if e["type"] == "TRACK_IDENTITY_SUSPECT"]
    assert len(suspects) == 1
    assert (suspects[0]["a"], suspects[0]["b"]) == ("spreader", "spreader_2")
    assert suspects[0]["grade"] == "OBSERVED"


def test_tracks_expose_visibility_and_station_coordinates(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = _pipeline(pcfg, station)
    p.process_frame(
        render_frame(glove_px=mm_to_px(GLOVE_MM), markers_px={10: mm_to_px(TOOL_MM)}), 0
    )
    assert p._tracker is not None
    tracks, _ = p._tracker.update(
        FRAME_MS,
        None,
        [],
        p._H,  # type: ignore[arg-type]
    )
    assert tracks["gloves"].visible is False and tracks["gloves"].last_seen_ms == 0
    assert tracks["spreader"].visible is False and tracks["spreader"].marker_id == 10
    assert tracks["gloves"].contact_point_mm is not None
    gx, gy = tracks["gloves"].contact_point_mm
    assert abs(gx - GLOVE_MM[0]) < 5 and abs(gy - GLOVE_MM[1]) < 5
    assert tracks["gloves"].radius_mm >= 40.0
    assert tracks["spreader"].radius_mm == pcfg.tool_size_mm * 2
