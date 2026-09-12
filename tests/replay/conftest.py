"""Shared helpers for the replay suite. Tests (unlike src/replay) may import runtime to build
the (Config, StationConfig, Knowledge) triple a fixture names in its `config` block."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import pytest

from src.replay import ScenarioFile, load_scenario

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "scenarios"
CANONICAL = tuple("ABCDEFGHIJKLM")


def scenario_paths() -> list[Path]:
    return sorted(SCENARIO_DIR.glob("*.yaml"))


def scenario_ids() -> list[str]:
    return [p.stem for p in scenario_paths()]


@cache
def loaded_for(profile: str, station: str, knowledge: str) -> Any:
    from src.runtime.config import load

    return load(ROOT / "config", profile, station, knowledge, environ={})


@cache
def core_for(profile: str, station: str, knowledge: str) -> Any:
    from src.runtime.config import to_domain

    return to_domain(loaded_for(profile, station, knowledge))


def core_of(scenario: ScenarioFile) -> Any:
    c = scenario.config
    return core_for(c.profile, c.station, c.knowledge)


def runner_of(scenario: ScenarioFile) -> Any:
    from src.replay.runner import ReplayRunner

    cfg, station, k = core_of(scenario)
    return ReplayRunner(cfg, station, k)


@pytest.fixture(params=scenario_paths(), ids=scenario_ids())
def scenario(request: pytest.FixtureRequest) -> ScenarioFile:
    return load_scenario(request.param)
