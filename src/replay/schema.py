"""Scenario v1 shorthand from 36, retaining typed semantic event validation at expansion."""

from typing import Literal

from pydantic import Field, JsonValue

from src.domain import Alert, Config, Knowledge, Model, StationConfig, TraceStep, WorldState


class ScenarioConfig(Model):
    station: str
    knowledge: str
    profile: str
    overrides: dict[str, JsonValue] = Field(default_factory=dict)


class ScenarioFile(Model):
    scenario: str
    description: str
    schema_version: Literal[1] = 1
    config: ScenarioConfig
    initial_state: dict[str, JsonValue] = Field(default_factory=dict)
    events: list[dict[str, JsonValue]]
    expect: list[dict[str, JsonValue]]
    # CONTRACT-GAP: optional embedded versioned inputs enable self-contained offline fixtures.
    config_bundle: Config | None = None
    station_bundle: StationConfig | None = None
    knowledge_bundle: Knowledge | None = None
    failure_modes: list[str] = Field(default_factory=list)
    hazard: bool = False


class AssertionResult(Model):
    assertion: dict[str, JsonValue]
    passed: bool
    detail: str


class ReplayResult(Model):
    final_state: WorldState
    alerts: list[Alert]
    traces: list[TraceStep]
    assertions: list[AssertionResult]
