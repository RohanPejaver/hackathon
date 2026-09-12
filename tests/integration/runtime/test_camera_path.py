"""The live perception path through the composition root: a video file stands in for the
camera; the pipeline's events reach the same log, reducer and policy as everything else, and
the controller — not perception — decides the mode (22 RuntimeController, ADR-0011)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
os.environ["STATION_NO_AUTOSTART"] = "1"
sys.path.insert(0, str(Path("tests/perception").resolve()))

from synth import DEFAULT_CORNERS_PX, mm_to_px, render_frame, write_video  # noqa: E402

from src.runtime.app import build  # noqa: E402


def test_video_drives_the_runtime_into_full_and_taints_the_gloves(tmp_path: Path):
    frames = []
    pesto = mm_to_px((170, 470))  # inside bin:pesto (70-270 x 370-570)
    for _ in range(45):  # 3 s at 15 fps: dwell satisfied many times over
        frames.append(
            render_frame(
                corners_px=DEFAULT_CORNERS_PX, glove_px=pesto, markers_px={10: mm_to_px((150, 260))}
            )
        )
    video = tmp_path / "clip.mp4"
    write_video(str(video), frames, fps=15)
    rt = build(log_dir=tmp_path, camera=str(video))
    assert rt.controller.mode() == "PROTOCOL_ONLY"  # until frames prove healthy
    deadline = time.time() + 15
    while time.time() < deadline and (rt.pipeline is None or rt._pipeline_handle.thread.is_alive()):
        rt.tick()
        time.sleep(0.05)
    for _ in range(12):
        rt.tick()
        time.sleep(0.1)
    types = [e.type for e in rt.recent]
    assert "ZONE_ENTRY" in types, types
    gloves = rt.state.station.carriers["gloves"]
    assert "PINE_NUT" in gloves.taints, gloves
    assert rt.pipeline.health().healthy
    rt.stop_perception()
