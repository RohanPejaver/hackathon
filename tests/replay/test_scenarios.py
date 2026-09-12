"""L2 / the P1 gate (38): every fixture A-M and the demo runs end to end through the reasoning
core with zero perception, and every assertion in it holds."""

from __future__ import annotations

from src.replay import ScenarioFile

from .conftest import runner_of


def test_scenario_passes(scenario: ScenarioFile) -> None:
    result = runner_of(scenario).run(scenario)
    assert not result.rejected, [r.model_dump() for r in result.rejected]
    failures = [f"{a.assertion}\n    -> {a.detail}" for a in result.assertions if not a.passed]
    assert not failures, f"{scenario.scenario}: {len(failures)} assertion(s) failed:\n" + "\n".join(
        failures
    )
    assert result.passed
    assert len(result.assertions) == len(scenario.expect)
