"""The wire shape: A's DisplayPayload (state_summary + interventions) verbatim, plus B's
runtime block. The mock validates against the pydantic models the schema is generated from.
Three epistemic values only (13); no SAFE anywhere (02); no identity fields (24)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain import Alert, DisplayPayload
from src.ui import wire

MOCK = Path("src/ui/static/mock")


def _example() -> dict:
    return json.loads((MOCK / "snapshot.example.json").read_text())


def test_example_validates_and_covers_the_handshake_minimum():
    s = wire.Snapshot.model_validate(_example())
    assert {int(a.tier) for a in s.interventions} == {0, 1, 2}
    assert {c.epistemic for c in s.state_summary.carriers} == {"TRACKED", "STALE", "UNKNOWN"}
    assert any(st.rule_id == "absence" for a in s.interventions for st in a.derivation)
    assert any("2 hops" in st.narrative for a in s.interventions for st in a.derivation)
    # the A-owned half is exactly A's DisplayPayload
    DisplayPayload.model_validate({"state_summary": _example()["state_summary"], "interventions": _example()["interventions"]})


def test_schema_file_is_generated_from_the_models():
    on_disk = json.loads((MOCK / "snapshot.schema.json").read_text())
    assert on_disk == wire.Snapshot.model_json_schema(), "run: python -m src.ui.wire"


def test_exactly_three_epistemic_values_and_no_safe_member_or_identity():
    schema = json.dumps(wire.Snapshot.model_json_schema())
    assert '"enum": ["TRACKED", "STALE", "UNKNOWN"]' in schema
    for bad in ("SAFE", "UNOBSERVED", "SUSPECT", '"name"', '"worker_id"', '"customer"', '"employee"'):
        assert bad not in schema, bad


def test_shape_is_closed_and_headlines_cannot_claim_safety():
    s = _example()
    s["extra"] = 1
    with pytest.raises(ValidationError):
        wire.Snapshot.model_validate(s)
    a = dict(_example()["interventions"][0])
    a["headline"] = "Food is safe to send"
    with pytest.raises(ValidationError):
        Alert.model_validate(a)
    a["headline"] = "one two three four five six seven"
    with pytest.raises(ValidationError):
        Alert.model_validate(a)
