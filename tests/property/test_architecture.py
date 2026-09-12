"""Mechanical guards required before semantic streams begin."""
import ast
from pathlib import Path

from src.events import EVENT_ADAPTER, EVENT_TYPES, project

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("domain", "events", "state", "risk", "policy", "orders", "knowledge", "replay")


def clock_violations(source: str) -> list[int]:
    tree = ast.parse(source)
    return [node.lineno for node in ast.walk(tree) if (
        isinstance(node, (ast.Import, ast.ImportFrom))
        and ((isinstance(node, ast.Import) and any(n.name in {"time", "datetime"} for n in node.names))
             or (isinstance(node, ast.ImportFrom) and node.module in {"time", "datetime"}))
    ) or (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
          and node.func.attr in {"now", "utcnow", "time", "monotonic", "perf_counter"})]


def test_no_clock_in_core() -> None:
    for package in PACKAGES:
        for file in (ROOT / "src" / package).rglob("*.py"):
            assert not clock_violations(file.read_text()), str(file)


def test_clock_guard_rejects_violation() -> None:
    assert clock_violations("from datetime import datetime\nx = datetime.now()")


def event_examples() -> list[dict[str, object]]:
    import src.events.catalog as catalog
    result: list[dict[str, object]] = []
    values: dict[str, object] = {
        "a": "gloves", "b": "board", "carrier": "gloves", "zone": "pesto",
        "contact_point": {"x": 0, "y": 0}, "depth": 1.0, "duration_ms": 100,
        "dwell_ms": 100, "worker_slot": 0, "phase": "DON", "retired": "spreader",
        "introduced": "spreader2", "from_zone": "stock", "claim": "CLEAN",
        "ticket": "T1", "items": ["sandwich"], "restrictions": [], "reason": "test",
        "alert_id": "a1", "rework_of": "T0", "mode": "PROTOCOL_ONLY", "cause": "test",
        "epistemic": "UNKNOWN", "config_version": "1", "knowledge_version": "1",
        "pathway_signature": "sig",
    }
    for index, kind in enumerate(EVENT_TYPES):
        cls = getattr(catalog, "".join(part.title() for part in kind.split("_")))
        data: dict[str, object] = {
            "type": kind, "event_id": f"e{index}", "seq": index, "t_occurred": index,
            "t_committed": index, "station_id": "station", "source": "OPERATOR",
            "grade": "ASSERTED" if kind in {"WASH_CYCLE", "OPERATOR_ASSERTION"} else "OBSERVED",
        }
        for field, definition in cls.model_fields.items():
            if definition.is_required() and field not in data:
                data[field] = values[field]
        result.append(data)
    return result


def test_every_event_round_trips_without_binary_fields() -> None:
    examples = event_examples()
    assert len(examples) == len(EVENT_TYPES)
    for example in examples:
        event = EVENT_ADAPTER.validate_python(example)
        assert EVENT_ADAPTER.validate_json(event.model_dump_json()) == event
        assert "confidence" not in project(event).model_dump()
        assert "binary" not in str(type(event).model_json_schema()).lower()


def test_confidence_projection_invariant() -> None:
    for example in event_examples():
        low = EVENT_ADAPTER.validate_python({**example, "confidence": 0.01})
        high = EVENT_ADAPTER.validate_python({**example, "confidence": 0.99})
        assert project(low).model_dump_json() == project(high).model_dump_json()


def prohibited_copy(text: str) -> bool:
    import re
    return bool(re.search(r"\b(safe|contaminated|contamination|allergen-free)\b", text, re.I))


def test_alert_copy_guard() -> None:
    assert prohibited_copy("This food is safe")
    file = ROOT / "src/policy/copy.py"
    if file.exists():
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not prohibited_copy(node.value)
