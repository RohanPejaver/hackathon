"""BUILD_B §1.5: the wire shape is frozen once published. The mock is the example, verbatim,
and both validate against the pydantic models the schema is generated from. Three epistemic
values only (13); no SAFE anywhere (02); no identity fields (24)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.ui import wire

MOCK = Path("src/ui/static/mock")


def test_example_validates_and_covers_the_handshake_minimum():
    s = wire.Snapshot.model_validate_json((MOCK / "snapshot.example.json").read_text())
    assert {a.tier for a in s.alerts} == {0, 1, 2}
    assert {c.epistemic for c in s.carriers} == {"TRACKED", "STALE", "UNKNOWN"}
    two_hop = [a for a in s.alerts if any("hop 2" in (st.state_delta or "") for st in a.derivation)]
    assert two_hop, "example must carry a two-hop evidence trace"
    assert any(st.kind == "ABSENCE" for a in s.alerts for st in a.derivation)


def test_schema_file_is_generated_from_the_models():
    on_disk = json.loads((MOCK / "snapshot.schema.json").read_text())
    assert on_disk == wire.Snapshot.model_json_schema(), "run: python -m src.ui.wire"


def test_exactly_three_epistemic_values_and_no_safe_member():
    schema = json.dumps(wire.Snapshot.model_json_schema())
    assert '"enum": ["TRACKED", "STALE", "UNKNOWN"]' in schema
    assert "SAFE" not in schema and "UNOBSERVED" not in schema and "SUSPECT" not in schema
    for word in ("name", "worker_id", "customer", "employee"):
        assert f'"{word}"' not in schema, word


def test_shape_is_closed_and_headlines_cannot_claim_safety():
    s = json.loads((MOCK / "snapshot.example.json").read_text())
    s["extra"] = 1
    with pytest.raises(ValidationError):
        wire.Snapshot.model_validate(s)
    a = dict(json.loads((MOCK / "snapshot.example.json").read_text())["alerts"][0])
    a["headline"] = "Food is safe to send"
    with pytest.raises(ValidationError):
        wire.Alert.model_validate(a)
    a["headline"] = "one two three four five six seven"
    with pytest.raises(ValidationError):
        wire.Alert.model_validate(a)
