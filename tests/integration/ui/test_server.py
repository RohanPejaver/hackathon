"""39 §6: two routes, full state over the socket, POST /action is the only write and it is an
event, not a state mutation. The snapshot here is an opaque dict — the wire shape is tested
separately against the frozen schema (test_snapshot_shape.py)."""

from fastapi.testclient import TestClient

from src.ui.server import create_app


def _app(actions: list[dict]):
    state = {"seq": 0}

    def snapshot():
        state["seq"] += 1
        return {"seq": state["seq"]}

    def on_action(body):
        actions.append(body)
        return {"accepted": True, "event_id": f"evt-{len(actions)}"}

    return create_app(snapshot, on_action, push_hz=50.0)


def test_routes_and_no_write_but_action():
    app = _app([])
    routes = {(r.path, tuple(sorted(r.methods))) for r in app.routes if hasattr(r, "methods")}
    assert ("/", ("GET",)) in routes
    assert ("/inspector", ("GET",)) in routes
    writes = [p for p, m in routes if "POST" in m or "PUT" in m or "DELETE" in m]
    assert writes == ["/action"]


def test_pages_serve_vendored_assets_only():
    client = TestClient(_app([]))
    for path in ("/", "/inspector"):
        html = client.get(path).text
        assert "http://" not in html and "https://" not in html, path
        assert "cdn" not in html.lower(), path


def test_action_becomes_an_event_and_socket_pushes_full_state():
    actions: list[dict] = []
    client = TestClient(_app(actions))
    r = client.post("/action", json={"kind": "ACKNOWLEDGE", "alert_id": "a1"})
    assert r.status_code == 200 and r.json()["accepted"]
    assert actions == [{"kind": "ACKNOWLEDGE", "alert_id": "a1"}]
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        second = ws.receive_json()
    assert second["seq"] > first["seq"]
