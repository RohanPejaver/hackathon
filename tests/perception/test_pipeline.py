"""Pipeline contract: every payload validates as a DraftEvent and is JSON (no pixels, 24);
end-to-end over a synthetic mp4 through `start(...)`, an `EventSink` and the committed log;
importing perception never loads the safety core (10 §The mandatory boundary)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from src.domain import StationConfig
from src.events import DRAFTEVENT_ADAPTER, EventLog, EventSink
from src.perception.config import PerceptionConfig
from src.perception.pipeline import PerceptionPipeline

from .conftest import FRAME_MS, ROOT, build_pcfg
from .synth import mm_to_px, render_frame, write_video

PESTO_MM = (170.0, 470.0)
TOOL_MM = (500.0, 40.0)
NEAR_TOOL_MM = (600.0, 40.0)  # in contact range without occluding the marker
LANDING_MM = (870.0, 190.0)


def _lerp(a: tuple[float, float], b: tuple[float, float], f: float) -> tuple[float, float]:
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def scripted_frames() -> list[NDArray[np.uint8]]:
    """6 s at 15 fps: glove at bin:pesto -> onto the spreader marker -> onto the landing."""
    tool = {10: mm_to_px(TOOL_MM)}
    frames: list[NDArray[np.uint8]] = []
    for i in range(90):
        if i < 20:
            g = PESTO_MM
        elif i < 35:
            g = _lerp(PESTO_MM, NEAR_TOOL_MM, (i - 20) / 15)
        elif i < 55:
            g = NEAR_TOOL_MM
        elif i < 70:
            g = _lerp(NEAR_TOOL_MM, LANDING_MM, (i - 55) / 15)
        else:
            g = LANDING_MM
        frames.append(render_frame(glove_px=mm_to_px(g), markers_px=tool, marker_size_px=64))
    return frames


def _assert_serializable(payload: dict[str, object]) -> None:
    DRAFTEVENT_ADAPTER.validate_python(payload)
    text = json.dumps(payload)
    assert "ndarray" not in text and "bytes" not in text
    for v in payload.values():
        assert not isinstance(v, np.ndarray | bytes | bytearray | memoryview)


def test_every_payload_validates_and_is_json(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = PerceptionPipeline()
    p.configure(pcfg, station)
    payloads: list[dict[str, object]] = []
    for i, frame in enumerate(scripted_frames()):
        payloads += p.process_frame(frame, i * FRAME_MS)
    payloads += p.check(90 * FRAME_MS + 5000)
    assert len(payloads) >= 5
    for payload in payloads:
        _assert_serializable(payload)
        assert payload["source"] == "PERCEPTION"
        assert payload["station_id"] == pcfg.station_id
        assert str(payload["event_id"]).startswith("pc-")
    ids = [payload["event_id"] for payload in payloads]
    assert len(set(ids)) == len(ids)


def test_uncalibrated_frames_emit_only_health(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = PerceptionPipeline()
    p.configure(pcfg, station)
    blank = render_frame(corners_px={}, glove_px=mm_to_px(PESTO_MM))
    events = p.process_frame(blank, 0)
    assert [e["cause"] for e in events] == ["uncalibrated"]
    assert p.vision_state == "UNAVAILABLE" and "uncalibrated" in p.health().causes
    assert p.process_frame(blank, FRAME_MS) == []  # once per transition
    events = p.process_frame(render_frame(glove_px=mm_to_px(PESTO_MM)), 2 * FRAME_MS)
    assert p.vision_state == "OK" and p.health().healthy
    assert all(e["type"] != "HEALTH_DEGRADED" for e in events)


def test_fixed_homography_from_config_skips_self_calibration(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    p = PerceptionPipeline()
    p.configure(pcfg, station)
    p.process_frame(render_frame(), 0)
    assert p._H is not None
    fixed = PerceptionConfig.build(
        **{
            **{f: getattr(pcfg, f) for f in pcfg.__dataclass_fields__},
            "homography": tuple(tuple(float(v) for v in row) for row in p._H.tolist()),
        }
    )
    q = PerceptionPipeline()
    q.configure(fixed, station)
    events = q.process_frame(render_frame(corners_px={}, glove_px=mm_to_px(PESTO_MM)), 0)
    assert all(e["cause"] != "uncalibrated" for e in events if e["type"] == "HEALTH_DEGRADED")
    assert q.vision_state == "OK"


def test_end_to_end_video_through_sink_and_log(
    loaded: object, station: StationConfig, tmp_path: Path
) -> None:
    video = tmp_path / "scripted.mp4"
    write_video(video, scripted_frames(), fps=15)
    cfg = build_pcfg(loaded, camera_source=str(video), realtime=False)  # type: ignore[arg-type]
    log = EventLog(500)
    sink = EventSink(log, lambda: 0)
    pipeline = PerceptionPipeline()
    handle = pipeline.start(cfg, station, sink)
    assert handle.thread is not None
    handle.thread.join(timeout=60)
    assert not handle.thread.is_alive()
    pipeline.stop(handle)
    log._drain(10_000, force=True)
    committed = list(log.read(0))
    assert log._quarantine == []
    kinds = [(e.type, getattr(e, "a", None), getattr(e, "b", None)) for e in committed]
    entries = [
        i
        for i, e in enumerate(committed)
        if e.type == "ZONE_ENTRY" and e.carrier == "gloves" and e.zone == "bin:pesto"  # type: ignore[union-attr]
    ]
    tool = [i for i, k in enumerate(kinds) if k == ("CONTACT_BEGIN", "gloves", "spreader")]
    landing = [i for i, k in enumerate(kinds) if k == ("CONTACT_BEGIN", "gloves", "landing")]
    assert entries and tool and landing, kinds
    assert entries[0] < tool[0] < landing[0]
    assert all(e.source == "PERCEPTION" for e in committed)
    assert pipeline.health().healthy is True
    assert pipeline.vision_state == "OK"


def test_camera_unavailable_reports_and_retries(
    loaded: object, station: StationConfig, tmp_path: Path
) -> None:
    cfg = build_pcfg(loaded, camera_source=str(tmp_path / "missing.mp4"))  # type: ignore[arg-type]
    log = EventLog(0)
    sink = EventSink(log, lambda: 0)
    pipeline = PerceptionPipeline()
    handle = pipeline.start(cfg, station, sink)
    assert handle.thread is not None
    handle.thread.join(timeout=1.0)  # the thread stays alive, retrying every 2 s
    assert handle.thread.is_alive()
    assert pipeline.vision_state == "UNAVAILABLE"
    assert "camera unavailable" in pipeline.health().causes
    pipeline.stop(handle)
    assert not handle.thread.is_alive()
    log._drain(0, force=True)
    assert [e.cause for e in log.read(0) if e.type == "HEALTH_DEGRADED"] == ["camera unavailable"]  # type: ignore[union-attr]


def test_importing_perception_does_not_load_the_safety_core() -> None:
    code = (
        "import sys; import src.perception.pipeline; "
        "print(sorted(m for m in sys.modules if m.startswith('src.')))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    loaded = out.stdout.strip()
    for forbidden in ("src.state", "src.risk", "src.policy", "src.orders", "src.runtime", "src.ui"):
        assert forbidden not in loaded, loaded
