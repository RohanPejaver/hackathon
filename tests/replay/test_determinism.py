"""L2: the determinism contract (36). Each fixture run twice — through a fresh runner the
second time — produces byte-identical output. A fixture that is not reproducible is a
defect in the runtime, not in the fixture."""

from __future__ import annotations

from src.replay import ScenarioFile

from .conftest import runner_of


def test_two_runs_are_byte_identical(scenario: ScenarioFile) -> None:
    first = runner_of(scenario).run(scenario).model_dump_json()
    second = runner_of(scenario).run(scenario).model_dump_json()
    assert first == second
