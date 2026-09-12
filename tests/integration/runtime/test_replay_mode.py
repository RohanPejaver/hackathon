"""37 §Determinism under pressure: the fallback ladder. The runtime in REPLAY mode, fed from
`scenarios/demo.yaml` (level 3) or from a recorded session log (level 2), must reach the same
alerts and ticket states as `ReplayRunner` on the same fixture — identical UI from all levels."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["STATION_NO_AUTOSTART"] = "1"

from src.replay import load_scenario  # noqa: E402
from src.replay.runner import ReplayRunner  # noqa: E402
from src.runtime.app import Runtime, build  # noqa: E402
from src.runtime.clock import LogClock  # noqa: E402
from src.runtime.config import load, to_domain  # noqa: E402

DEMO = Path("scenarios/demo.yaml")


def _drain(rt: Runtime, upto: int) -> None:
    clock = rt.clock
    assert isinstance(clock, LogClock)
    rt.feed_until(upto)
    for _ in range(3):
        clock.advance_to(clock.now() + rt.cfg.t_reorder + 1)
        rt.tick()


def _summary(alerts, tickets) -> dict:
    return {
        "alerts": sorted((int(a.tier), a.ticket_id, a.allergen_id, a.state) for a in alerts),
        "tickets": sorted((t.ticket_id, t.lifecycle) for t in tickets),
    }


def test_runtime_replay_of_demo_matches_the_replay_runner(tmp_path: Path):
    rt = build(log_dir=tmp_path, replay=DEMO)
    assert rt.controller.mode() == "REPLAY"
    # beat 3: Tier 0 before any motion on ticket 48
    _drain(rt, 9_000)
    snap = rt.snapshot()
    tier0 = [a for a in snap["interventions"] if a["tier"] == 0]
    assert tier0 and tier0[0]["ticket_id"] == "T48"
    assert {"gloves", "spreader", "board", "bin:mayo"} <= set(tier0[0]["blocking_carriers"])
    # to the end: same alerts and ticket lifecycles as the pure runner
    _drain(rt, 10**9)
    live = _summary(rt.alerts.all(), rt.state.tickets.values())
    cfg, station, k = to_domain(load("config", "eval", "demo", "demo", environ={}))
    result = ReplayRunner(cfg, station, k).run(load_scenario(DEMO))
    pure = _summary(result.alerts, result.final_state.tickets.values())
    assert live == pure
    assert any(t[3] == "ESCALATED" and t[0] == 2 for t in live["alerts"]), live


def test_recorded_log_replays_to_the_same_end_state(tmp_path: Path):
    first = build(log_dir=tmp_path, replay=DEMO)
    _drain(first, 10**9)
    (log_path,) = list(tmp_path.glob("*.jsonl"))
    assert log_path.stat().st_size > 0
    second = build(log_dir=None, replay=log_path)
    _drain(second, 10**9)
    assert _summary(second.alerts.all(), second.state.tickets.values()) == _summary(
        first.alerts.all(), first.state.tickets.values()
    )
