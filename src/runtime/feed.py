"""REPLAY mode inputs (10 §Runtime modes): layers 1–4 replaced by a log reader.

Two sources, one shape: a scenario fixture (36) or a recorded session log (39 §5 JSONL).
Either becomes a time-ordered list of *drafts* that the runtime re-emits through the same
`EventSink` the perception thread would use, paced by the runtime tick. Derived events in a
recorded log (`ALERT_*`, `TICKET_HELD`, the runtime's own `CONFIG_LOADED` /
`STATION_MODE_CHANGED` / `HEALTH_DEGRADED`) are outputs of the fold and are re-derived, never
replayed. A fixture's `TICKET_RECEIVED` is followed by intake, exactly as the runner does it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.events import DRAFTEVENT_ADAPTER, EVENT_ADAPTER, DraftEvent
from src.replay import ScenarioFile, build_event, load_scenario, sorted_events

DERIVED_TYPES = {"TICKET_HELD", "CONFIG_LOADED", "STATION_MODE_CHANGED", "HEALTH_DEGRADED"}


@dataclass(frozen=True)
class FeedItem:
    t: int
    draft: DraftEvent
    needs_intake: bool  # fixture TICKET_RECEIVED: run the normalizer, as the runner does


def _to_draft(event: Any) -> DraftEvent:
    return DRAFTEVENT_ADAPTER.validate_python(
        event.model_dump(exclude={"seq", "t_committed", "late"})
    )


def scenario_feed(
    path: Path | str, station_id: str
) -> tuple[ScenarioFile, list[FeedItem], dict[str, Any]]:
    """Returns the scenario, its inputs as drafts, and the part of `initial_state` that must
    still be patched into the state (taint seeds). Epistemic seeds become real
    `CARRIER_OBSERVABILITY_CHANGED` events at the log origin so that a session log recorded
    from this replay is self-contained (Q8: seeds as synthesized provenance).
    CONTRACT-GAP: 36 has no event form for a seeded taint; a recorded log of a taint-seeded
    fixture is not self-contained — level 3 of the ladder (the fixture itself) covers those."""
    scenario = load_scenario(path)
    items: list[FeedItem] = []
    for index, raw in sorted_events(scenario):
        event = build_event(raw, scenario=scenario.scenario, seq=index, station_id=station_id)
        items.append(FeedItem(event.t_occurred, _to_draft(event), event.type == "TICKET_RECEIVED"))
    origin = min((i.t for i in items), default=0)
    carriers = scenario.initial_state.get("carriers", {})
    taint_seed: dict[str, Any] = {"carriers": {}}
    seeds: list[FeedItem] = []
    if isinstance(carriers, dict):
        for cid, spec in carriers.items():
            if not isinstance(spec, dict):
                continue
            if "epistemic" in spec:
                draft = DRAFTEVENT_ADAPTER.validate_python(
                    {
                        "type": "CARRIER_OBSERVABILITY_CHANGED",
                        "event_id": f"{scenario.scenario}:-seed:{cid}",  # sorts before ":0000"
                        "t_occurred": origin,
                        "station_id": station_id,
                        "source": "PERCEPTION",
                        "grade": "OBSERVED",
                        "carrier": cid,
                        "epistemic": spec["epistemic"],
                        "cause": "scenario seed",
                    }
                )
                seeds.append(FeedItem(origin, draft, False))
            rest = {k: v for k, v in spec.items() if k != "epistemic"}
            if rest:
                taint_seed["carriers"][cid] = rest
    return scenario, seeds + items, taint_seed


def jsonl_feed(path: Path | str) -> list[FeedItem]:
    items: list[FeedItem] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        event = EVENT_ADAPTER.validate_json(line)
        derived = event.source == "SYSTEM" and (
            event.type.startswith("ALERT_") or event.type in DERIVED_TYPES
        )
        if derived:
            continue
        items.append(FeedItem(event.t_occurred, _to_draft(event), False))
    items.sort(key=lambda i: (i.t, i.draft.event_id))
    return items
