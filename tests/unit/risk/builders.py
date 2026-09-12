"""Hand-built WorldState fixtures (33 §Risk engine). Never imports src.state."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from src.domain import (
    Carrier,
    CarrierKind,
    Config,
    ContactEdge,
    EpistemicStatus,
    EvidenceGrade,
    Knowledge,
    Mode,
    ResetKind,
    ResetRecord,
    Resolution,
    Restriction,
    Station,
    Strength,
    TaintRecord,
    Ticket,
    TicketLifecycle,
    WorldState,
    Zone,
    ZoneKind,
)
from src.knowledge import load_bundle

ROOT = Path(__file__).resolve().parents[3]
DEMO_KNOWLEDGE = ROOT / "config" / "knowledge" / "demo"
STATION_ID = "demo-bagel"

_KINDS: dict[str, CarrierKind] = {
    "gloves": CarrierKind.GLOVES,
    "spreader": CarrierKind.TOOL,
    "board": CarrierKind.SURFACE,
    "landing": CarrierKind.SURFACE,
    "bin:pesto": CarrierKind.CONTAINER,
    "bin:mayo": CarrierKind.CONTAINER,
    "bin:turkey": CarrierKind.CONTAINER,
    "bin:bread": CarrierKind.CONTAINER,
}
_RESETS: dict[CarrierKind, frozenset[ResetKind]] = {
    CarrierKind.GLOVES: frozenset({ResetKind.GLOVE_CHANGE}),
    CarrierKind.TOOL: frozenset(
        {ResetKind.TOOL_SWAP, ResetKind.WASH_CYCLE, ResetKind.OPERATOR_ASSERTION}
    ),
    CarrierKind.SURFACE: frozenset({ResetKind.SURFACE_SWAP, ResetKind.OPERATOR_ASSERTION}),
    CarrierKind.CONTAINER: frozenset({ResetKind.OPERATOR_ASSERTION}),
    CarrierKind.FOOD: frozenset(),
}
ZONE_ALLERGENS: dict[str, dict[str, Strength]] = {
    "bin:pesto": {
        "PINE_NUT": Strength.PRESENT,
        "MILK": Strength.PRESENT,
        "TREE_NUT": Strength.POSSIBLE,
    },
    "bin:mayo": {"EGG": Strength.PRESENT},
    "bin:bread": {"WHEAT": Strength.PRESENT, "SESAME": Strength.POSSIBLE, "SOY": Strength.POSSIBLE},
}


def cfg(**over: Any) -> Config:
    base: dict[str, Any] = dict(
        config_version="1",
        knowledge_version="1",
        max_hops=3,
        t_reorder=500,
        t_stale={
            CarrierKind.GLOVES: 20_000,
            CarrierKind.TOOL: 120_000,
            CarrierKind.SURFACE: 300_000,
            CarrierKind.CONTAINER: 600_000,
            CarrierKind.FOOD: 300_000,
        },
        t_occlusion_max=3_000,
        station_recent_window=1_800_000,
        t_escalate=20_000,
        t_cooldown=120_000,
        t_abandon=900_000,
        t_dwell=250,
        t_hysteresis=400,
        t_recover=10_000,
        t_manager=60_000,
        threshold_observed={},
        threshold_inferred={},
        normalizer_threshold=0.8,
        strength_decay_per_hop=[Strength.PRESENT, Strength.PRESENT, Strength.POSSIBLE],
    )
    base.update(over)
    return Config(**base)


@lru_cache(maxsize=1)
def knowledge() -> Knowledge:
    return load_bundle(DEMO_KNOWLEDGE)


def taint(
    allergen: str,
    t: int,
    event: str = "e-src",
    source: str = "bin:pesto",
    grade: EvidenceGrade = EvidenceGrade.OBSERVED,
    hops: int = 0,
    strength: Strength = Strength.PRESENT,
) -> TaintRecord:
    return TaintRecord(
        allergen_id=allergen,
        acquired_at=t,
        source_event_id=event,
        source_carrier_id=source,
        grade=grade,
        hops=hops,
        strength=strength,
    )


def carrier(
    cid: str,
    kind: CarrierKind | None = None,
    *,
    t_observed: int | None = 0,
    epistemic: EpistemicStatus = EpistemicStatus.TRACKED,
    taints: dict[str, TaintRecord] | None = None,
) -> Carrier:
    kind = kind or _KINDS.get(cid, CarrierKind.TOOL)
    return Carrier(
        carrier_id=cid,
        kind=kind,
        taints=taints or {},
        epistemic=epistemic,
        last_observed_at=t_observed,
        resettable_by=_RESETS[kind],
    )


def food(tid: str) -> Carrier:
    return carrier(f"food:{tid}", CarrierKind.FOOD)


def demo_zones() -> dict[str, Zone]:
    zones = {
        "bin:pesto": Zone(
            zone_id="bin:pesto",
            kind=ZoneKind.INGREDIENT,
            contents=["pesto"],
            bound_carrier="bin:pesto",
        ),
        "bin:mayo": Zone(
            zone_id="bin:mayo",
            kind=ZoneKind.INGREDIENT,
            contents=["mayo"],
            bound_carrier="bin:mayo",
        ),
        "bin:turkey": Zone(
            zone_id="bin:turkey",
            kind=ZoneKind.INGREDIENT,
            contents=["turkey"],
            bound_carrier="bin:turkey",
        ),
        "bin:bread": Zone(
            zone_id="bin:bread",
            kind=ZoneKind.INGREDIENT,
            contents=["bread"],
            bound_carrier="bin:bread",
        ),
        "work": Zone(zone_id="work", kind=ZoneKind.WORK, bound_carrier="board"),
        "landing": Zone(zone_id="landing", kind=ZoneKind.LANDING, bound_carrier="landing"),
        "tool_rack": Zone(zone_id="tool_rack", kind=ZoneKind.TOOL_RACK),
        "clean_stock": Zone(zone_id="clean_stock", kind=ZoneKind.CLEAN_STOCK),
        "glove_dispenser": Zone(zone_id="glove_dispenser", kind=ZoneKind.GLOVE_DISPENSER),
        "wash": Zone(zone_id="wash", kind=ZoneKind.WASH),
    }
    return zones


def demo_station(
    *,
    t: int = 0,
    mode: Mode = Mode.FULL,
    epistemic: EpistemicStatus = EpistemicStatus.TRACKED,
    observed: bool = True,
    carriers: dict[str, Carrier] | None = None,
    extra: list[Carrier] = (),  # type: ignore[assignment]
    recent: dict[str, int] | None = None,
) -> Station:
    """The demo station (config/station/demo.yaml). Every carrier TRACKED and observed at
    `t` unless overridden; `carriers` replaces individual entries; `extra` adds (food)."""
    base = {
        cid: carrier(cid, kind, t_observed=t if observed else None, epistemic=epistemic)
        for cid, kind in _KINDS.items()
    }
    base.update(carriers or {})
    for c in extra:
        base[c.carrier_id] = c
    return Station(
        station_id=STATION_ID,
        config_version="1",
        knowledge_version="1",
        mode=mode,
        carriers=base,
        zones=demo_zones(),
        worker_slots=1,
        recent_allergen_exposure=recent or {},
    )


def edge(
    eid: str, t: int, a: str, b: str, grade: EvidenceGrade = EvidenceGrade.OBSERVED
) -> ContactEdge:
    return ContactEdge(event_id=eid, t_occurred=t, a=a, b=b, grade=grade)


def reset(
    eid: str,
    t: int,
    cid: str,
    grade: EvidenceGrade = EvidenceGrade.OBSERVED,
    operator: bool = False,
) -> ResetRecord:
    return ResetRecord(event_id=eid, t_occurred=t, carrier_id=cid, grade=grade, operator=operator)


def ticket(
    tid: str = "T48",
    items: tuple[str, ...] = ("turkey_sandwich",),
    allergens: tuple[str, ...] = ("PINE_NUT",),
    lifecycle: TicketLifecycle = TicketLifecycle.BOUND,
    resolution: Resolution = Resolution.RESOLVED,
) -> Ticket:
    restrictions = (
        [
            Restriction(
                allergen_ids=frozenset(allergens),
                raw_text=" ".join(allergens).lower(),
                resolution=resolution,
            )
        ]
        if allergens
        else []
    )
    return Ticket(
        ticket_id=tid,
        items=list(items),
        restrictions=restrictions,
        lifecycle=lifecycle,
        bound_station=STATION_ID,
    )


def state(
    station: Station | None = None,
    *,
    t: int = 0,
    contacts: list[ContactEdge] = (),  # type: ignore[assignment]
    resets: list[ResetRecord] = (),  # type: ignore[assignment]
    acquisitions: dict[str, list[TaintRecord]] | None = None,
    tickets: list[Ticket] = (),  # type: ignore[assignment]
    conditions: list[str] = (),  # type: ignore[assignment]
    last_event_id: str = "e-last",
    last_event_type: str = "CONTACT_BEGIN",
) -> WorldState:
    return WorldState(
        station=station or demo_station(t=t),
        tickets={tk.ticket_id: tk for tk in tickets},
        contacts=list(contacts),
        resets=list(resets),
        acquisitions=acquisitions or {},
        zone_allergens=ZONE_ALLERGENS,
        t_occurred=t,
        last_event_id=last_event_id,
        last_event_type=last_event_type,
        conditions=list(conditions),
    )
