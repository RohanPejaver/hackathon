"""Fixtures for reducer tests: a small station (03 header: bins pesto/mayo, carriers
gloves/spreader/board/landing) and a graded-event builder."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pytest

from src.domain import (
    Carrier,
    CarrierKind,
    Config,
    Mode,
    ResetKind,
    StateDelta,
    StationConfig,
    Strength,
    WorldState,
    Zone,
    ZoneKind,
)
from src.events import GRADEDEVENT_ADAPTER, GradedEvent
from src.state import initial, reduce

STATION_ID = "demo-bagel"

PERCEPTION = {
    "CONTACT_BEGIN",
    "CONTACT_END",
    "ZONE_ENTRY",
    "ZONE_EXIT",
    "GLOVE_CHANGE",
    "TOOL_SWAP",
    "SURFACE_SWAP",
    "WASH_CYCLE",
    "SURFACE_WIPE",
    "CARRIER_OBSERVABILITY_CHANGED",
    "TRACK_IDENTITY_SUSPECT",
}
OPERATOR = {"TICKET_BOUND", "TICKET_RELEASED", "OPERATOR_ASSERTION"}
ASSERTED = {"WASH_CYCLE", "OPERATOR_ASSERTION"}


def make_config(**overrides: Any) -> Config:
    base: dict[str, Any] = {
        "config_version": "cfg-1",
        "knowledge_version": "k-1",
        "max_hops": 3,
        "t_reorder": 500,
        "t_stale": {
            CarrierKind.GLOVES: 20_000,
            CarrierKind.TOOL: 120_000,
            CarrierKind.SURFACE: 300_000,
            CarrierKind.CONTAINER: 600_000,
            CarrierKind.FOOD: 300_000,
        },
        "t_occlusion_max": 3_000,
        "station_recent_window": 1_800_000,
        "t_escalate": 20_000,
        "t_cooldown": 120_000,
        "t_abandon": 900_000,
        "t_dwell": 250,
        "t_hysteresis": 400,
        "t_recover": 10_000,
        "t_manager": 60_000,
        "threshold_observed": {"ZONE_ENTRY": 0.85},
        "threshold_inferred": {"ZONE_ENTRY": 0.60},
        "normalizer_threshold": 0.8,
        "strength_decay_per_hop": [Strength.PRESENT, Strength.PRESENT, Strength.POSSIBLE],
    }
    base.update(overrides)
    return Config(**base)


def make_station(mode: Mode = Mode.FULL) -> StationConfig:
    def zone(zone_id: str, kind: ZoneKind, bound: str | None, contents: list[str]) -> Zone:
        return Zone(zone_id=zone_id, kind=kind, bound_carrier=bound, contents=contents)

    def carrier(
        carrier_id: str, kind: CarrierKind, home: str | None, *resets: ResetKind
    ) -> Carrier:
        return Carrier(
            carrier_id=carrier_id, kind=kind, home_zone=home, resettable_by=frozenset(resets)
        )

    zones = [
        zone("bin:pesto", ZoneKind.INGREDIENT, "bin:pesto", ["pesto"]),
        zone("bin:mayo", ZoneKind.INGREDIENT, "bin:mayo", ["mayo"]),
        zone("work", ZoneKind.WORK, "board", []),
        zone("landing", ZoneKind.LANDING, "landing", []),
        zone("clean_stock", ZoneKind.CLEAN_STOCK, None, []),
        zone("glove_dispenser", ZoneKind.GLOVE_DISPENSER, None, []),
        zone("wash", ZoneKind.WASH, None, []),
        zone("tool_rack", ZoneKind.TOOL_RACK, None, []),
    ]
    carriers = [
        carrier("gloves", CarrierKind.GLOVES, None, ResetKind.GLOVE_CHANGE),
        carrier(
            "spreader",
            CarrierKind.TOOL,
            "tool_rack",
            ResetKind.TOOL_SWAP,
            ResetKind.WASH_CYCLE,
            ResetKind.OPERATOR_ASSERTION,
        ),
        carrier("board", CarrierKind.SURFACE, "work", ResetKind.SURFACE_SWAP),
        carrier("landing", CarrierKind.SURFACE, "landing", ResetKind.SURFACE_SWAP),
        carrier("bin:pesto", CarrierKind.CONTAINER, "bin:pesto", ResetKind.OPERATOR_ASSERTION),
        carrier("bin:mayo", CarrierKind.CONTAINER, "bin:mayo", ResetKind.OPERATOR_ASSERTION),
    ]
    return StationConfig(
        station_id=STATION_ID,
        config_version="cfg-1",
        knowledge_version="k-1",
        mode=mode,
        worker_slots=1,
        carriers={c.carrier_id: c for c in carriers},
        zones={z.zone_id: z for z in zones},
        zone_allergens={
            "bin:pesto": {"PINE_NUT": Strength.PRESENT, "MILK": Strength.PRESENT},
            "bin:mayo": {"EGG": Strength.PRESENT},
        },
    )


_counter = {"n": 0}


def ev(kind: str, t: int, **fields: Any) -> GradedEvent:
    """Build a graded event with sensible envelope defaults; any envelope field can be
    overridden through `fields` (event_id, source, grade, station_id, seq)."""
    _counter["n"] += 1
    n = _counter["n"]
    source = "PERCEPTION" if kind in PERCEPTION else "SYSTEM"
    if kind in OPERATOR:
        source = "OPERATOR"
    elif kind.startswith("TICKET_"):
        source = "ORDER_SYSTEM"
    data: dict[str, Any] = {
        "type": kind,
        "event_id": f"e{n}",
        "seq": n,
        "t_occurred": t,
        "t_committed": t,
        "station_id": STATION_ID,
        "source": source,
        "grade": "ASSERTED" if kind in ASSERTED else "OBSERVED",
    }
    data.update(fields)
    return GRADEDEVENT_ADAPTER.validate_python(data)


def fold(state: WorldState, events: Iterable[GradedEvent], cfg: Config) -> WorldState:
    for e in events:
        state, _ = reduce(state, e, cfg)
    return state


def fold_deltas(
    state: WorldState, events: Iterable[GradedEvent], cfg: Config
) -> tuple[WorldState, list[StateDelta]]:
    out: list[StateDelta] = []
    for e in events:
        state, deltas = reduce(state, e, cfg)
        out.extend(deltas)
    return state, out


# Common building blocks -----------------------------------------------------------------


def zone_entry(t: int, carrier: str, zone: str, **fields: Any) -> GradedEvent:
    return ev("ZONE_ENTRY", t, carrier=carrier, zone=zone, depth=1.0, **fields)


def contact(t: int, a: str, b: str, **fields: Any) -> GradedEvent:
    return ev("CONTACT_BEGIN", t, a=a, b=b, contact_point={"x": 0.0, "y": 0.0}, **fields)


def glove_don(t: int, slot: int = 0, **fields: Any) -> GradedEvent:
    return ev("GLOVE_CHANGE", t, worker_slot=slot, phase="DON", **fields)


def ticket_received(t: int, ticket: str, *allergens: str, **fields: Any) -> GradedEvent:
    restrictions = [
        {
            "allergen_ids": list(allergens),
            "raw_text": " ".join(allergens) or "none",
            "resolution": "RESOLVED",
            "severity_declared": "STATED_ALLERGY",
        }
    ]
    if not allergens:
        restrictions = []
    return ev(
        "TICKET_RECEIVED",
        t,
        ticket=ticket,
        items=["turkey_sandwich"],
        restrictions=fields.pop("restrictions", restrictions),
        **fields,
    )


def ticket_bound(t: int, ticket: str, **fields: Any) -> GradedEvent:
    return ev("TICKET_BOUND", t, ticket=ticket, worker_slot=0, **fields)


@pytest.fixture
def cfg() -> Config:
    return make_config()


@pytest.fixture
def station() -> StationConfig:
    return make_station()


@pytest.fixture
def state(cfg: Config, station: StationConfig) -> WorldState:
    return initial(cfg, station)


@pytest.fixture
def bound_ticket(state: WorldState, cfg: Config) -> WorldState:
    """A PINE_NUT ticket T1 already BOUND (landing zone `landing`)."""
    return fold(state, [ticket_received(10, "T1", "PINE_NUT"), ticket_bound(20, "T1")], cfg)
