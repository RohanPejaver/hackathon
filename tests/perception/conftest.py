"""The whole perception suite skips when opencv is absent (39 §2: the core is testable
without a camera library; perception is not). This is the ONLY skip in the package."""

from __future__ import annotations

from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")

from src.domain import StationConfig  # noqa: E402
from src.perception.config import PerceptionConfig  # noqa: E402
from src.runtime.config import LoadedConfig, load, to_domain  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FPS = 15
FRAME_MS = 66  # tests step at i * 66 ms (~15 fps)


@pytest.fixture(scope="session")
def loaded() -> LoadedConfig:
    return load(ROOT / "config", "eval", "demo", "demo", environ={})


@pytest.fixture(scope="session")
def station(loaded: LoadedConfig) -> StationConfig:
    _cfg, station, _knowledge = to_domain(loaded)
    assert isinstance(station, StationConfig)
    return station


def build_pcfg(loaded: LoadedConfig, **overrides: object) -> PerceptionConfig:
    v = loaded.values
    p = v.perception
    kwargs: dict[str, object] = dict(
        station_id=loaded.station.station_id,
        width_mm=loaded.station.calibration.width_mm,
        height_mm=loaded.station.calibration.height_mm,
        homography=None,
        fps=FPS,
        t_dwell_ms=250,
        t_hysteresis_ms=400,
        t_occlusion_max_ms=3000,
        heartbeat_ms=8000,
        threshold_observed={k: t.observed for k, t in p.thresholds.items()},
        threshold_inferred={k: t.inferred for k, t in p.thresholds.items()},
        camera_source=p.camera.source,
        marker_dictionary=p.markers.dictionary,
        corner_ids=tuple(p.markers.corner_ids),
        corner_size_mm=p.markers.corner_size_mm,
        tool_size_mm=p.markers.tool_size_mm,
        hsv_lower=p.gloves.hsv_lower,
        hsv_upper=p.gloves.hsv_upper,
        min_area_px=p.gloves.min_area_px,
        glove_change_absence_ms=int(p.glove_change_absence_s * 1000),
        frame_timeout_ms=int(p.health.frame_timeout_s * 1000),
        static_frames=p.health.static_frames,
        frame_rate_floor_fps=p.frame_rate_floor_fps,
        tool_markers=dict(loaded.station.markers.tools),
        surface_markers=dict(loaded.station.markers.surfaces),
        realtime=False,
    )
    kwargs.update(overrides)
    return PerceptionConfig.build(**kwargs)  # type: ignore[arg-type]


@pytest.fixture
def pcfg(loaded: LoadedConfig) -> PerceptionConfig:
    return build_pcfg(loaded)
