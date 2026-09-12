"""39 §7: the layer DAG (22, 30) is enforced by an import-linter contract, mechanically.

Three checks: the contract set is non-empty and names every rule in 30; `lint-imports` is
wired into the suite and passes on the real tree; and a deliberately planted violation
(a `state/` module importing `perception/`) is rejected — a rule that has never rejected
anything is not enforced. The plant is made in a copy of `src/`, never in the real tree.
"""

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = ROOT / "pyproject.toml"


def _contracts() -> list[dict]:
    return tomllib.loads(PYPROJECT.read_text())["tool"]["importlinter"]["contracts"]


def _lint(cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    exe = Path(sys.executable).parent / "lint-imports"
    return subprocess.run(
        [str(exe), "--config", str(cwd / "pyproject.toml")],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def test_contract_set_covers_every_rule_in_30():
    names = " ".join(c["name"] for c in _contracts())
    assert len(_contracts()) >= 5
    for rule in ("rule 1", "rule 2", "rule 3", "rule 4", "rule 5"):
        assert rule in names, f"{rule} has no import-linter contract"


def test_lint_imports_passes_on_the_real_tree():
    r = _lint(ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_planted_violation_in_state_is_rejected(tmp_path: Path):
    shutil.copytree(ROOT / "src", tmp_path / "src")
    shutil.copy(PYPROJECT, tmp_path / "pyproject.toml")
    (tmp_path / "src" / "state" / "_planted_violation.py").write_text(
        "import src.perception  # planted: state must never import perception\n"
    )
    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    r = _lint(tmp_path, env)
    assert r.returncode != 0, "lint-imports accepted a state -> perception import"
    assert "rule 3" in r.stdout, r.stdout + r.stderr
