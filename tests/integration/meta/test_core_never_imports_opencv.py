"""39 §2 / ADR-0001: the safety core must import and run with opencv absent, even when the
perception extra is installed. The composition root reaches perception only lazily."""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_importing_the_core_and_runtime_does_not_load_cv2():
    code = (
        "import sys, os; os.environ['STATION_NO_AUTOSTART']='1'; "
        "import src.domain, src.events, src.state, src.risk, src.policy, src.orders, "
        "src.knowledge, src.replay, src.runtime.app, src.ui.server; "
        "print(sorted(m for m in sys.modules "
        "if m in ('cv2', 'numpy', 'mediapipe', 'src.perception')))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    loaded = out.stdout.strip()
    assert "cv2" not in loaded and "src.perception" not in loaded, loaded


def test_runtime_has_no_module_scope_perception_import():
    for path in (ROOT / "src" / "runtime").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:  # module scope only; lazy imports inside functions are allowed
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not any(n.startswith(("src.perception", "cv2", "numpy")) for n in names), path
