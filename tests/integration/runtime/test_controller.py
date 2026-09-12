"""22 RuntimeController invariants: the only owner of mode transitions; every transition is an
event with a cause; CALIBRATION refuses FULL on bad config and blocks binding; vision loss
degrades, recovery re-enters FULL after t_recover; a core exception never fails open."""

from src.runtime.clock import LogClock
from src.runtime.controller import RuntimeController


def _ctl(initial="CALIBRATION"):
    events: list[dict] = []
    clock = LogClock(0)
    c = RuntimeController(events.append, clock, t_recover_s=10, initial=initial)
    return c, events, clock


def test_bad_config_stays_in_calibration_and_refuses_full():
    c, events, _ = _ctl()
    c.report_config(False, "station zone bin:pesto: contents ingredient 'pestoo' does not resolve")
    c.report_vision("OK")
    c.request_mode("FULL", "operator")
    assert c.mode() == "CALIBRATION" and events == []
    assert "does not resolve" in c.health()["message"]
    assert not c.bind_allowed()


def test_every_transition_is_exactly_one_event_with_cause():
    c, events, _ = _ctl()
    c.report_config(True)
    c.request_mode("PROTOCOL_ONLY", "no camera attached")
    c.request_mode("PROTOCOL_ONLY", "again")
    assert c.mode() == "PROTOCOL_ONLY" and len(events) == 1
    assert events[0]["type"] == "STATION_MODE_CHANGED"
    assert events[0]["payload"] == {
        "mode": "PROTOCOL_ONLY",
        "previous": "CALIBRATION",
        "cause": "no camera attached",
    }
    assert c.bind_allowed()


def test_vision_loss_degrades_and_recovery_needs_t_recover():
    c, events, clock = _ctl()
    c.report_config(True)
    c.report_vision("OK")
    c.request_mode("FULL", "startup")
    assert c.mode() == "FULL"
    c.report_vision("UNAVAILABLE")
    assert c.mode() == "PROTOCOL_ONLY" and events[-1]["payload"]["cause"] == "vision unavailable"
    clock.advance_to(5_000)
    c.report_vision("OK")
    assert c.mode() == "PROTOCOL_ONLY", "must stay degraded until t_recover elapses"
    clock.advance_to(9_000)
    c.report_vision("OK")
    assert c.mode() == "PROTOCOL_ONLY"
    clock.advance_to(15_000)
    c.report_vision("OK")
    assert c.mode() == "FULL" and events[-1]["payload"]["cause"] == "vision healthy for t_recover"


def test_core_exception_enters_protocol_only_and_never_fails_open():
    c, events, clock = _ctl()
    c.report_config(True)
    c.report_vision("OK")
    c.request_mode("FULL", "startup")
    c.report_core_exception("evt-0042", ValueError("reducer blew up"))
    h = c.health()
    assert c.mode() == "PROTOCOL_ONLY"
    assert h["reasoning"] == "DOWN" and h["last_incident_event_id"] == "evt-0042"
    assert "evt-0042" in h["message"] and "ValueError" in h["message"]
    clock.advance_to(60_000)
    c.report_vision("OK")
    assert c.mode() == "PROTOCOL_ONLY", (
        "healthy vision must not re-enter FULL while reasoning is down"
    )


def test_health_counts_late_and_rejected():
    c, _, _ = _ctl()
    c.report_committed(False)
    c.report_committed(True)
    c.report_rejected()
    h = c.health()
    assert h["late_rate"] == 0.5 and h["rejected_events"] == 1
