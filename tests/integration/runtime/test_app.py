"""P3 gate, mechanically: a complete demo path runs in PROTOCOL_ONLY with no camera attached,
through the real composition root and the real HTTP surface. Ticket intake, bind, Tier 0 before
any motion, one-tap assertion, resolution, hold release. Worker actions enter only as events.

Needs the P1 packages (state/risk/policy/orders/knowledge); it is the outer-loop test for them."""

from __future__ import annotations

import os

import pytest

os.environ["STATION_NO_AUTOSTART"] = "1"

from src.runtime.app import Runtime, build  # noqa: E402
from src.runtime.clock import LogClock  # noqa: E402
from src.runtime.config import load  # noqa: E402


@pytest.fixture
def rt() -> Runtime:
    """A PROTOCOL_ONLY runtime on a LogClock so the reorder window is stepped deterministically."""
    loaded = load("config", "demo", "demo", "demo", environ={})
    clock = LogClock(0)
    r = Runtime(loaded, clock, log_dir=None)
    r.tick()
    r.controller.report_vision("UNAVAILABLE")
    r.controller.request_mode("PROTOCOL_ONLY", "no perception pipeline configured")
    _settle(r)
    return r


def _settle(r: Runtime, steps: int = 3) -> None:
    """Advance the log clock past t_reorder so pending drafts commit."""
    clock = r.clock
    assert isinstance(clock, LogClock)
    for _ in range(steps):
        clock.advance_to(clock.now() + r.cfg.t_reorder + 1)
        r.tick()


def _types(r: Runtime) -> list[str]:
    return [e.type for e in r.recent]


def _open(snap: dict) -> list[dict]:
    return [
        a for a in snap["interventions"] if a["state"] in ("RAISED", "ACKNOWLEDGED", "ESCALATED")
    ]


def _new_ticket(r: Runtime, ticket_id: str, item: str, note: str | None = None) -> None:
    restrictions = [{"raw_text": note}] if note else []
    r.on_action(
        {
            "kind": "NEW_TICKET",
            "ticket_id": ticket_id,
            "items": [item],
            "restrictions": restrictions,
        }
    )


def test_starts_in_protocol_only_with_config_loaded_first(rt: Runtime):
    types = _types(rt)
    assert types[0] == "CONFIG_LOADED"
    assert "STATION_MODE_CHANGED" in types
    snap = rt.snapshot()
    assert snap["state_summary"]["mode"] == "PROTOCOL_ONLY"
    assert snap["runtime"]["health"]["vision"] == "UNAVAILABLE"
    assert all(c["epistemic"] == "UNKNOWN" for c in snap["state_summary"]["carriers"])
    assert snap["interventions"] == []


def test_unrestricted_ticket_is_silent(rt: Runtime):
    _new_ticket(rt, "T47", "pesto_sandwich")
    _settle(rt)
    assert rt.on_action({"kind": "BIND_TICKET", "ticket_id": "T47"})["accepted"]
    _settle(rt)
    snap = rt.snapshot()
    assert [t["lifecycle"] for t in snap["state_summary"]["tickets"]] == ["BOUND"]
    assert _open(snap) == []


def test_restricted_bind_fires_tier0_before_any_motion_and_resolves_in_one_tap(rt: Runtime):
    _new_ticket(rt, "T48", "turkey_sandwich", "pine nut allergy")
    _settle(rt)
    snap = rt.snapshot()
    (ticket,) = snap["state_summary"]["tickets"]
    assert ticket["lifecycle"] == "RECEIVED"
    assert ticket["restrictions"][0]["resolution"] == "RESOLVED"
    assert ticket["restrictions"][0]["allergen_ids"] == ["PINE_NUT"]
    assert rt.on_action({"kind": "BIND_TICKET", "ticket_id": "T48"})["accepted"]
    _settle(rt)
    snap = rt.snapshot()
    (alert,) = snap["interventions"]
    assert alert["tier"] == 0 and alert["ticket_id"] == "T48" and alert["allergen_id"] == "PINE_NUT"
    assert "gloves" in alert["blocking_carriers"]
    assert len(alert["headline"].split()) <= 7
    # every required carrier is UNKNOWN in PROTOCOL_ONLY, so every one needs a reset
    blocking = set(alert["blocking_carriers"])
    assert {"gloves", "board", "landing", "bin:bread", "bin:turkey", "bin:mayo"} <= blocking
    # one tap: assert all — enters the log as OPERATOR_ASSERTION events, never a state write
    r = rt.on_action(
        {"kind": "ASSERT_REPLACED", "alert_id": alert["alert_id"], "carrier_ids": sorted(blocking)}
    )
    assert r["accepted"] and len(r["event_ids"]) == len(blocking)
    _settle(rt)
    snap = rt.snapshot()
    assert _open(snap) == [], snap["interventions"]
    # 16: the resolution is shown, not silently cleared — the resolved alert lingers briefly
    assert [a["state"] for a in snap["interventions"]] == ["RESOLVED_BY_ASSERTION"]
    types = _types(rt)
    assert types.count("OPERATOR_ASSERTION") == len(blocking)
    assert "ALERT_RESOLVED" in types
    resolved = [a for a in rt.alerts.all() if a.alert_id == alert["alert_id"]]
    assert resolved and resolved[0].state == "RESOLVED_BY_ASSERTION"


def test_ambiguous_restriction_blocks_binding(rt: Runtime):
    _new_ticket(rt, "T50", "pesto_sandwich", "ALLERGY")
    _settle(rt)
    snap = rt.snapshot()
    assert snap["state_summary"]["tickets"][0]["lifecycle"] == "BLOCKED"
    assert not rt.on_action({"kind": "BIND_TICKET", "ticket_id": "T50"})["accepted"]
    _settle(rt)
    assert "TICKET_BOUND" not in _types(rt)


def test_hold_is_only_released_by_a_person(rt: Runtime):
    _new_ticket(rt, "T51", "turkey_sandwich", "pine nut allergy")
    _settle(rt)
    rt.on_action({"kind": "BIND_TICKET", "ticket_id": "T51"})
    _settle(rt)
    rt.on_action({"kind": "PREP_STARTED", "ticket_id": "T51"})
    _settle(rt)
    rt.on_action({"kind": "ITEM_COMPLETE", "ticket_id": "T51"})
    _settle(rt)
    snap = rt.snapshot()
    (ticket,) = snap["state_summary"]["tickets"]
    # a Tier 0 prompt does not hold; no observed pathway exists
    assert ticket["lifecycle"] == "COMPLETE"
    (alert,) = snap["interventions"]
    assert alert["tier"] == 0
    assert not rt.on_action({"kind": "DISMISS", "alert_id": "nope"})["accepted"]
    assert rt.on_action({"kind": "RESOLVE_HOLD", "ticket_id": "T51"})["accepted"]
    _settle(rt)
    snap = rt.snapshot()
    assert snap["state_summary"]["tickets"][0]["lifecycle"] == "RELEASED"
    assert _open(snap) == [], "a released ticket leaves no intervention behind (26 §4)"


def test_bad_config_serves_a_calibration_stub_with_the_error(tmp_path, monkeypatch):
    import shutil

    from fastapi.testclient import TestClient

    from src.runtime.app import make_app

    shutil.copytree("config", tmp_path / "config")
    (tmp_path / "config" / "defaults.yaml").write_text("temporal: [unclosed\n")
    monkeypatch.setenv("STATION_CONFIG_ROOT", str(tmp_path / "config"))
    client = TestClient(make_app())
    snap = client.get("/snapshot").json()
    assert snap["state_summary"]["mode"] == "CALIBRATION"
    assert "YAML" in snap["runtime"]["health"]["message"]
    assert client.post("/action", json={"kind": "BIND_TICKET", "ticket_id": "x"}).status_code == 400


def test_malformed_action_never_crashes(rt: Runtime):
    assert rt.on_action({"kind": "BIND_TICKET"})["accepted"] is False
    assert rt.on_action({"kind": "NOPE"})["accepted"] is False
    assert rt.on_action({})["accepted"] is False


def test_snapshot_validates_against_the_wire_shape(rt: Runtime):
    from src.ui import wire

    wire.Snapshot.model_validate(rt.snapshot())


def test_build_boots_the_real_thing(tmp_path):
    r = build(log_dir=tmp_path)
    assert r.controller.mode() == "PROTOCOL_ONLY"
    assert list(tmp_path.glob("*.jsonl")), "session log is written as JSONL (39 §5)"
