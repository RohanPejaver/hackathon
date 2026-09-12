#!/usr/bin/env python
"""P1 gate artifact (38 §P1, 34 §Acceptance): run every scenario fixture twice, diff the
output byte-for-byte, and write `data/eval/<date>/p1_replay_report.json` with per-fixture
results, determinism, Intervention Recall and Silent Miss Rate. Exit non-zero if anything
fails. Metrics are recorded as an artifact, never asserted in prose.

Definitions (34):
  * intervention_before_complete — for every restricted ticket that was ever bound, some
    RAISE/ESCALATE for that ticket was issued no later than its TICKET_ITEM_COMPLETE (or
    at all, if it never completed).
  * silent_miss — a hazard fixture with no such intervention. Tier 0 fires by design
    whenever a required carrier is not TRACKED-clean, so "no intervention at all" is
    exactly the case where the system asserted TRACKED-clean and was wrong.
  * intervention_recall = interventions / hazard fixtures; silent_miss_rate = misses /
    hazard fixtures.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain import TicketLifecycle  # noqa: E402
from src.events import TicketItemComplete  # noqa: E402
from src.replay import ReplayResult, ScenarioFile, load_scenario  # noqa: E402
from src.replay.runner import ReplayRunner  # noqa: E402
from src.runtime.config import load, to_domain  # noqa: E402

_NEVER_BOUND = {TicketLifecycle.RECEIVED, TicketLifecycle.BLOCKED}


@cache
def _runner(profile: str, station: str, knowledge: str) -> ReplayRunner:
    cfg, station_cfg, k = to_domain(load(ROOT / "config", profile, station, knowledge, environ={}))
    return ReplayRunner(cfg, station_cfg, k)


def _fresh_runner(sf: ScenarioFile) -> ReplayRunner:
    c = sf.config
    cfg, station_cfg, k = to_domain(
        load(ROOT / "config", c.profile, c.station, c.knowledge, environ={})
    )
    return ReplayRunner(cfg, station_cfg, k)


def hazard_metrics(sf: ScenarioFile, result: ReplayResult) -> tuple[bool, bool]:
    restricted = sorted(
        tid
        for tid, t in result.final_state.tickets.items()
        if any(r.allergen_ids for r in t.restrictions) and t.lifecycle not in _NEVER_BOUND
    )
    complete_at: dict[str, int] = {}
    for e in result.events:
        if isinstance(e, TicketItemComplete):
            complete_at.setdefault(e.ticket, e.t_occurred)

    def intervened(tid: str) -> bool:
        return any(
            tc.command.kind in ("RAISE", "ESCALATE")
            and tc.command.alert.ticket_id == tid
            and (tid not in complete_at or tc.t <= complete_at[tid])
            for tc in result.commands
        )

    intervention = bool(restricted) and all(intervened(t) for t in restricted)
    silent_miss = sf.hazard and not intervention
    return intervention, silent_miss


def run_suite(scenario_dir: Path) -> dict[str, Any]:
    fixtures: dict[str, Any] = {}
    for path in sorted(scenario_dir.glob("*.yaml")):
        sf = load_scenario(path)
        c = sf.config
        first = _runner(c.profile, c.station, c.knowledge).run(sf)
        second = _fresh_runner(sf).run(sf)
        deterministic = first.model_dump_json() == second.model_dump_json()
        intervention, silent_miss = hazard_metrics(sf, first)
        fixtures[path.stem] = {
            "passed": first.passed and not first.rejected,
            "deterministic": deterministic,
            "hazard": sf.hazard,
            "intervention_before_complete": intervention,
            "silent_miss": silent_miss,
            "rejected": [r.model_dump() for r in first.rejected],
            "assertions": [a.model_dump() for a in first.assertions],
        }
    hazards = [f for f in fixtures.values() if f["hazard"]]
    interventions = sum(1 for f in hazards if f["intervention_before_complete"])
    misses = sum(1 for f in hazards if f["silent_miss"])
    all_passed = bool(fixtures) and all(
        f["passed"] and f["deterministic"] for f in fixtures.values()
    )
    return {
        "phase": "P1",
        "date": date.today().isoformat(),
        "fixtures": fixtures,
        "hazard_fixtures": len(hazards),
        "intervention_recall": interventions / len(hazards) if hazards else None,
        "silent_miss_rate": misses / len(hazards) if hazards else None,
        "all_passed": all_passed and misses == 0,
    }


def main() -> int:
    report = run_suite(ROOT / "scenarios")
    out_dir = ROOT / "data" / "eval" / report["date"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "p1_replay_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    fixtures = report["fixtures"]
    failed = sorted(n for n, f in fixtures.items() if not (f["passed"] and f["deterministic"]))
    print(
        f"P1 replay: {len(fixtures) - len(failed)}/{len(fixtures)} fixtures passed+deterministic; "
        f"IR={report['intervention_recall']} SMR={report['silent_miss_rate']} "
        f"(hazards={report['hazard_fixtures']}); failed={failed or 'none'}; report={out}"
    )
    for name in failed:
        for a in fixtures[name]["assertions"]:
            if not a["passed"]:
                print(f"  {name}: {a['assertion']} -> {a['detail']}")
        if not fixtures[name]["deterministic"]:
            print(f"  {name}: NOT DETERMINISTIC")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
