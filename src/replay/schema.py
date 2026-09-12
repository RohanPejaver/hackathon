"""Scenario v1 shorthand from 36, retaining typed semantic event validation at expansion.

`ScenarioFile` is the fixture on disk; `ReplayResult` is everything a run produced, kept
JSON-serializable and deterministic so two runs of one fixture can be diffed byte-for-byte
(36 §Determinism contract).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, JsonValue, model_validator

from src.domain import (
    Alert,
    AlertCommand,
    Config,
    Knowledge,
    Mode,
    Model,
    Pathway,
    StationConfig,
    TraceStep,
    WorldState,
)
from src.events import Event


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

    @model_validator(mode="after")
    def events_have_time_and_type(self) -> ScenarioFile:
        # `t` and `type` are the fixture's own ordering keys (36); a payload without them is a
        # malformed *file*, not a malformed event to be quarantined at run time.
        for index, raw in enumerate(self.events):
            t = raw.get("t")
            if isinstance(t, bool) or not isinstance(t, int):
                raise ValueError(f"events[{index}]: `t` must be an integer millisecond offset")
            if not isinstance(raw.get("type"), str):
                raise ValueError(f"events[{index}]: `type` must be an event type name")
        return self


class AssertionResult(Model):
    assertion: dict[str, JsonValue]
    passed: bool
    detail: str


class TimedCommand(Model):
    t: int
    command: AlertCommand


class StateSnapshot(Model):
    """State after the named committed event was folded (and any events it caused)."""

    t: int
    event_id: str
    state: WorldState


class ModeChange(Model):
    t: int
    mode: Mode


class Rejection(Model):
    """A malformed fixture event quarantined by the runner (23 P10), never crashed on."""

    index: int
    event_id: str
    reason: str


class TimedPathway(Model):
    t: int
    ticket_id: str
    pathway: Pathway


class ReplayResult(Model):
    scenario: str
    final_state: WorldState
    alerts: list[Alert] = Field(default_factory=list)
    traces: list[TraceStep] = Field(default_factory=list)
    assertions: list[AssertionResult] = Field(default_factory=list)
    passed: bool = False
    # CONTRACT-GAP: 22 names only the four fields above; the rest are what the assertion
    # vocabulary (36) is evaluated against and what the determinism diff covers.
    commands: list[TimedCommand] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)  # the whole committed log, seq order
    derived_events: list[Event] = Field(default_factory=list)  # subset the runner synthesized
    mode_timeline: list[ModeChange] = Field(default_factory=list)
    rejected: list[Rejection] = Field(default_factory=list)
    pathways: list[TimedPathway] = Field(default_factory=list)
    states: list[StateSnapshot] = Field(default_factory=list)
