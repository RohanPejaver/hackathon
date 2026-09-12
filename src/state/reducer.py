"""The pure reducer: `reduce(WorldState, GradedEvent, Config) -> (WorldState, [StateDelta])`.

Total, deterministic, no I/O, no clock, no randomness. Time is only `e.t_occurred` (19
§Clocks). The reducer branches on `grade`, never on `confidence` — the `GradedEvent`
projection has no such field (ADR-0004). Every row of the 13 transition table is a branch
below; rows that must do nothing (SURFACE_WIPE, ADR-0009) return the input state unchanged.

Convention: a mutating event that is *rejected* (unknown carrier or zone, duplicate ticket,
forbidden lifecycle transition) returns `(state, [])` with the identical state object. A
mutating event that is *applied* always stamps the envelope (t_occurred, last_event_*,
event_ids) even when it produced no field-level delta.
"""

from __future__ import annotations

from src.domain import (
    Carrier,
    CarrierKind,
    Config,
    EpistemicStatus,
    EvidenceGrade,
    Mode,
    ResetKind,
    StateDelta,
    Station,
    StationConfig,
    TicketLifecycle,
    WorldState,
    ZoneKind,
)
from src.events import GradedEvent
from src.events.catalog import (
    GradedCarrierObservabilityChanged,
    GradedConfigLoaded,
    GradedContactBegin,
    GradedGloveChange,
    GradedOperatorAssertion,
    GradedStationModeChanged,
    GradedSurfaceSwap,
    GradedTicketBlocked,
    GradedTicketBound,
    GradedTicketHeld,
    GradedTicketItemComplete,
    GradedTicketItemSubstituted,
    GradedTicketPrepStarted,
    GradedTicketReceived,
    GradedTicketReleased,
    GradedTicketRestrictionResolved,
    GradedTicketReworkOpened,
    GradedTicketVoided,
    GradedToolSwap,
    GradedTrackIdentitySuspect,
    GradedWashCycle,
    GradedZoneEntry,
)

from . import tickets as tk
from ._draft import Draft
from .taint import acquire_from_zone, merge_identity, propagate

_SWAP_DEFAULT_RESETS: dict[CarrierKind, frozenset[ResetKind]] = {
    CarrierKind.TOOL: frozenset({ResetKind.TOOL_SWAP, ResetKind.WASH_CYCLE}),
    CarrierKind.SURFACE: frozenset({ResetKind.SURFACE_SWAP}),
}


def initial(cfg: Config, station: StationConfig) -> WorldState:
    """Station start: carriers exactly as configured (all UNKNOWN until observed, 13), no
    tickets, no history, t_occurred = 0."""
    return WorldState(
        station=Station(
            station_id=station.station_id,
            config_version=station.config_version,
            knowledge_version=station.knowledge_version,
            mode=station.mode,
            carriers=dict(station.carriers),
            zones=dict(station.zones),
            bound_tickets=[],
            worker_slots=station.worker_slots,
            recent_allergen_exposure={},
        ),
        zone_allergens={z: dict(p) for z, p in station.zone_allergens.items()},
        t_occurred=0,
    )


def reduce(state: WorldState, e: GradedEvent, cfg: Config) -> tuple[WorldState, list[StateDelta]]:
    if not e.mutates_state:
        return state, []  # CONTACT_END, ZONE_EXIT, SURFACE_WIPE, HEALTH_DEGRADED, ALERT_*
    draft = Draft.open(state, e.event_id, e.t_occurred)
    if not _apply(draft, e, cfg, state):
        return state, []
    return draft.finalize(e.type, e.source)


def _apply(draft: Draft, e: GradedEvent, cfg: Config, state: WorldState) -> bool:
    """Returns False when the event is rejected (no effect at all)."""
    if isinstance(e, GradedZoneEntry):
        return _zone_entry(draft, e, cfg)
    if isinstance(e, GradedContactBegin):
        return _contact_begin(draft, e, cfg)
    if isinstance(e, GradedGloveChange):
        return _glove_change(draft, e)
    if isinstance(e, (GradedToolSwap, GradedSurfaceSwap)):
        return _swap(draft, e)
    if isinstance(e, GradedWashCycle):
        return _wash_cycle(draft, e)
    if isinstance(e, GradedOperatorAssertion):
        return _operator_assertion(draft, e)
    if isinstance(e, GradedCarrierObservabilityChanged):
        return _observability(draft, e)
    if isinstance(e, GradedTrackIdentitySuspect):
        return _identity_suspect(draft, e)
    if isinstance(e, GradedStationModeChanged):
        return _mode_change(draft, e)
    if isinstance(e, GradedConfigLoaded):
        draft.set_station_field("config_loaded", "config_version", e.config_version)
        draft.set_station_field("config_loaded", "knowledge_version", e.knowledge_version)
        return True
    if isinstance(e, GradedTicketReceived):
        return tk.received(draft, e)
    if isinstance(e, GradedTicketRestrictionResolved):
        return tk.restriction_resolved(draft, e)
    if isinstance(e, GradedTicketBlocked):
        return tk.blocked(draft, e)
    if isinstance(e, GradedTicketBound):
        return tk.bound(draft, e, state.station.station_id)
    if isinstance(e, GradedTicketPrepStarted):
        return tk.prep_started(draft, e)
    if isinstance(e, GradedTicketItemComplete):
        return tk.item_complete(draft, e)
    if isinstance(e, GradedTicketHeld):
        return tk.held(draft, e)
    if isinstance(e, GradedTicketReleased):
        return tk.released(draft, e)
    if isinstance(e, GradedTicketVoided):
        return tk.voided(draft, e)
    if isinstance(e, GradedTicketReworkOpened):
        return tk.rework_opened(draft, e)
    if isinstance(e, GradedTicketItemSubstituted):
        return tk.item_substituted(draft, e)
    return False  # total: an unrecognised mutating event changes nothing


# -- contact / acquisition ------------------------------------------------------------------


def _zone_entry(draft: Draft, e: GradedZoneEntry, cfg: Config) -> bool:
    zone = draft.zones.get(e.zone)
    if zone is None or e.carrier not in draft.carriers:
        return False
    # CONTRACT-GAP: 13 does not say whether a ZONE_ENTRY/CONTACT_BEGIN from a non-PERCEPTION
    # source counts as an observation; 12 catalogs these types as perception-sourced and
    # 36 fixtures omit `source`, so the event *type* is taken as the observation claim.
    draft.observe(e.carrier)
    acquire_from_zone(draft, e.carrier, e.zone, e.grade)
    if zone.bound_carrier and zone.bound_carrier != e.carrier:
        if zone.bound_carrier in draft.carriers:
            propagate(draft, e.carrier, zone.bound_carrier, e.grade, cfg)
    return True


def _contact_begin(draft: Draft, e: GradedContactBegin, cfg: Config) -> bool:
    left, right = _contact_targets(draft, e.a), _contact_targets(draft, e.b)
    if not left or not right:
        return False
    for carrier_id in sorted(set(left) | set(right)):
        draft.observe(carrier_id)
    seen: set[tuple[str, str]] = set()
    for x in left:
        for y in right:
            key = (min(x, y), max(x, y))
            if x == y or key in seen:
                continue
            seen.add(key)
            propagate(draft, x, y, e.grade, cfg)
    return True


def _contact_targets(draft: Draft, ident: str) -> list[str]:
    """A contact endpoint is a carrier id or a zone id (12: `b: CarrierId | ZoneId`). A zone
    stands for its bound carrier and, for a LANDING zone, every in-progress FOOD carrier
    resting there. A bin or landing surface shares its id with its zone (11 §Relationships),
    so both readings are taken and de-duplicated."""
    targets: list[str] = []
    if ident in draft.carriers:
        targets.append(ident)
    zone = draft.zones.get(ident)
    if zone is None:
        return targets
    if zone.bound_carrier and zone.bound_carrier in draft.carriers:
        if zone.bound_carrier not in targets:
            targets.append(zone.bound_carrier)
    if zone.kind == ZoneKind.LANDING:
        for ticket_id in sorted(draft.tickets):
            ticket = draft.tickets[ticket_id]
            food = tk.food_carrier_id(ticket_id)
            if (
                ticket.landing_zone == ident
                and ticket.lifecycle in (TicketLifecycle.IN_PREP, TicketLifecycle.COMPLETE)
                and food in draft.carriers
                and food not in targets
            ):
                targets.append(food)
    return targets


# -- resets (14 §Reset semantics) -----------------------------------------------------------


def _glove_change(draft: Draft, e: GradedGloveChange) -> bool:
    gloves = [
        c
        for c in sorted(draft.carriers.values(), key=lambda c: c.carrier_id)
        if c.kind == CarrierKind.GLOVES
    ]
    slot = [c for c in gloves if c.worker_slot == e.worker_slot]
    targets = slot or gloves
    if not targets:
        return False
    for carrier in targets:
        if e.phase == "DON":
            draft.clear_taints(
                "glove_change_reset",
                carrier,
                clean_grade=None,
                asserted_at=None,
                epistemic=EpistemicStatus.TRACKED,
                last_observed_at=draft.t,
            )
            draft.record_reset("glove_change_reset", carrier.carrier_id, e.grade, operator=False)
        else:
            draft.observe(carrier.carrier_id)
    return True


def _swap(draft: Draft, e: GradedToolSwap | GradedSurfaceSwap) -> bool:
    rule = "tool_swap" if isinstance(e, GradedToolSwap) else "surface_swap"
    default_kind = CarrierKind.TOOL if isinstance(e, GradedToolSwap) else CarrierKind.SURFACE
    retired = draft.carriers.get(e.retired)
    if retired is not None:
        if retired.kind == CarrierKind.FOOD:
            return False  # 11 inv. 7: no reset touches food
        draft.remove_carrier(rule, e.retired)
        draft.record_reset(rule, e.retired, e.grade, operator=False)
    existing = draft.carriers.get(e.introduced)
    if existing is not None and existing.kind == CarrierKind.FOOD:
        return False
    if existing is not None:
        # Re-introduced from CLEAN_STOCK: it carries the clean-stock state (13), observed now.
        draft.clear_taints(
            rule,
            existing,
            clean_grade=None,
            asserted_at=None,
            epistemic=EpistemicStatus.TRACKED,
            last_observed_at=draft.t,
        )
    else:
        kind = retired.kind if retired is not None else default_kind
        draft.add_carrier(
            rule,
            Carrier(
                carrier_id=e.introduced,
                kind=kind,
                taints={},
                epistemic=EpistemicStatus.TRACKED,
                last_observed_at=draft.t,
                home_zone=retired.home_zone if retired is not None else None,
                resettable_by=(
                    retired.resettable_by
                    if retired is not None
                    else _SWAP_DEFAULT_RESETS.get(kind, frozenset())
                ),
                worker_slot=retired.worker_slot if retired is not None else None,
            ),
        )
    draft.record_reset(rule, e.introduced, e.grade, operator=False)
    for zone_id in sorted(draft.zones):
        zone = draft.zones[zone_id]
        if zone.bound_carrier == e.retired and e.retired != e.introduced:
            draft.zones[zone_id] = zone.model_copy(update={"bound_carrier": e.introduced})
            draft.delta(rule, f"zones.{zone_id}.bound_carrier", e.retired, e.introduced)
    return True


def _wash_cycle(draft: Draft, e: GradedWashCycle) -> bool:
    carrier = draft.carriers.get(e.carrier)
    if carrier is None or carrier.kind == CarrierKind.FOOD:
        return False
    draft.clear_taints(
        "wash_cycle",
        carrier,
        clean_grade=EvidenceGrade.ASSERTED,
        asserted_at=draft.t,
        epistemic=EpistemicStatus.TRACKED,
        last_observed_at=draft.t,
    )
    draft.record_reset("wash_cycle", e.carrier, EvidenceGrade.ASSERTED, operator=False)
    return True


def _operator_assertion(draft: Draft, e: GradedOperatorAssertion) -> bool:
    carrier = draft.carriers.get(e.carrier)
    if carrier is None or carrier.kind == CarrierKind.FOOD:
        return False
    # CONTRACT-GAP: `resettable_by` (11) is advisory for policy action selection; the
    # reducer honours only the FOOD rule (11 inv. 7) and clears any other carrier on a
    # human assertion (14: "a human vouched; logged, never promoted").
    draft.clear_taints(
        "operator_assertion",
        carrier,
        clean_grade=EvidenceGrade.ASSERTED,
        asserted_at=draft.t,
    )
    draft.record_reset("operator_assertion", e.carrier, EvidenceGrade.ASSERTED, operator=True)
    return True


# -- epistemic / system ---------------------------------------------------------------------


def _observability(draft: Draft, e: GradedCarrierObservabilityChanged) -> bool:
    carrier = draft.carriers.get(e.carrier)
    if carrier is None:
        return False
    update: dict[str, object] = {"epistemic": e.epistemic}
    if e.epistemic == EpistemicStatus.TRACKED:
        update["last_observed_at"] = draft.t
    draft.set_carrier("observability", carrier, **update)
    return True


def _identity_suspect(draft: Draft, e: GradedTrackIdentitySuspect) -> bool:
    known = [c for c in (e.a, e.b) if c in draft.carriers]
    if not known:
        return False
    if len(known) == 2 and e.a != e.b:
        merge_identity(draft, e.a, e.b)
    for carrier_id in known:
        draft.set_carrier(
            "identity_merge", draft.carriers[carrier_id], epistemic=EpistemicStatus.STALE
        )
    return True


def _mode_change(draft: Draft, e: GradedStationModeChanged) -> bool:
    draft.set_station_field("mode_change", "mode", e.mode)
    if e.mode == Mode.PROTOCOL_ONLY:  # ADR-0011: vision is gone; nothing is verifiable
        for carrier_id in list(draft.carriers):
            draft.set_carrier(
                "mode_change", draft.carriers[carrier_id], epistemic=EpistemicStatus.UNKNOWN
            )
    return True
