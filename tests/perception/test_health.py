"""23 P5: frame starvation, static frames and low frame rate -> HEALTH_DEGRADED, once per
transition; status/state reflect every active cause."""

from __future__ import annotations

import numpy as np

from src.perception.config import PerceptionConfig
from src.perception.health import HealthMonitor

from .synth import render_frame


def _causes(drafts: list[dict[str, object]]) -> list[str]:
    assert all(d["type"] == "HEALTH_DEGRADED" for d in drafts)
    return [str(d["cause"]) for d in drafts]


def test_frame_starvation_once_per_outage(pcfg: PerceptionConfig) -> None:
    h = HealthMonitor(pcfg)
    assert h.state == "UNAVAILABLE"  # nothing seen yet is not "healthy"
    assert h.check(1_000) == []
    drafts = h.check(2_500)
    assert _causes(drafts) == ["frame starvation"]
    assert h.state == "UNAVAILABLE"
    assert not h.status().healthy and "frame starvation" in h.status().causes
    assert h.check(4_000) == []  # once per outage
    # frames resume: starvation clears, a fresh outage reports again
    assert h.on_frame(5_000, render_frame()) == []
    assert h.status().healthy and h.status().causes == []
    assert h.state == "OK"
    assert h.check(5_500) == []
    assert _causes(h.check(6_100)) == ["frame starvation"]


def test_static_frames_degrade_and_motion_clears(pcfg: PerceptionConfig) -> None:
    h = HealthMonitor(pcfg)
    still = render_frame(glove_px=(640, 360))
    events: list[dict[str, object]] = []
    for i in range(pcfg.static_frames):
        events += h.on_frame(i * 66, still)
    assert _causes(events) == ["static frame"]
    assert h.state == "DEGRADED"
    assert "static frame" in h.status().causes
    events = h.on_frame(pcfg.static_frames * 66, render_frame(glove_px=(700, 360)))
    assert events == []
    assert h.state == "OK" and h.status().healthy


def test_low_frame_rate(pcfg: PerceptionConfig) -> None:
    h = HealthMonitor(pcfg)
    frame = render_frame()
    events: list[dict[str, object]] = []
    for i in range(12):  # 4 fps for 3 s, floor is 8
        events += h.on_frame(i * 250, np.ascontiguousarray(frame))
        frame = render_frame(glove_px=(300 + 10 * i, 360))
    assert "low frame rate" in _causes(events)
    assert h.state == "DEGRADED"
