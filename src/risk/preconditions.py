"""Precondition check -> Tier 0 (15 §1). No graph search; uncertainty alone suffices."""

from __future__ import annotations

from src.domain import (
    Carrier,
    CarrierKind,
    Config,
    EpistemicStatus,
    Knowledge,
    Resolution,
    Ticket,
    WorldState,
    effective_epistemic,
)
from src.knowledge import KnowledgeProvider, matches


def restricted_allergens(ticket: Ticket, kp: KnowledgeProvider) -> frozenset[str]:
    """Union of closure(a) over every RESOLVED restriction; empty for unrestricted tickets."""
    out: set[str] = set()
    for r in ticket.restrictions:
        if r.resolution == Resolution.RESOLVED:
            for a in r.allergen_ids:
                out |= kp.closure(a)
    return frozenset(out)


def required_carriers(state: WorldState, ticket: Ticket, kp: KnowledgeProvider) -> list[str]:
    """Recipe-scoped carrier set (15, 18 §3): gloves, tools, then the carriers bound to the
    ticket's required zones in recipe order. Deterministic, deduplicated.

    CONTRACT-GAP: 15 writes `carriers_for(required_zones) U {GLOVES}` and MenuItemRecord has
    no required-tools field, yet product/03 scenario B, 25 §The evidence trace and 36's
    fixture example all list `spreader` in the Tier 0 checklist. TOOL-kind carriers are
    therefore treated like gloves: shared instruments, always required.
    """
    station = state.station
    out: list[str] = []
    for kind in (CarrierKind.GLOVES, CarrierKind.TOOL):
        for cid in sorted(station.carriers):
            if station.carriers[cid].kind == kind and cid not in out:
                out.append(cid)
    for item in ticket.items:
        for zone_id in kp.zones_for(item):
            zone = station.zones.get(zone_id)
            if zone is None or zone.bound_carrier is None:
                continue
            bound = zone.bound_carrier
            if bound in station.carriers and bound not in out:
                out.append(bound)
    return out


def pessimistic_allergens(
    state: WorldState, restricted: frozenset[str], cfg: Config
) -> frozenset[str]:
    """13 §Pessimistic closure, scoped to one restriction: allergens handled at the station
    within `station_recent_window` that fall inside `restricted`."""
    floor = state.t_occurred - cfg.station_recent_window
    return frozenset(
        a
        for a, t in state.station.recent_allergen_exposure.items()
        if t >= floor and matches(a, restricted)
    )


def matching_taints(carrier: Carrier, restricted: frozenset[str]) -> list[str]:
    ids = set(carrier.taints) | {t.allergen_id for t in carrier.taints.values()}
    return sorted(a for a in ids if matches(a, restricted))


def reset_since(state: WorldState, carrier_id: str, since: int | None) -> bool:
    """A valid reset (14: observed replacement or an ASSERTED assertion) on this carrier at or
    after `since`. Every reset the reducer records is in `state.resets`; SURFACE_WIPE never is."""
    if since is None:
        return False
    return any(r.carrier_id == carrier_id and r.t_occurred >= since for r in state.resets)


def needs_reset(
    state: WorldState,
    carrier: Carrier,
    restricted: frozenset[str],
    cfg: Config,
    since: int | None = None,
) -> bool:
    if matching_taints(carrier, restricted):
        return True
    if effective_epistemic(carrier, state.t_occurred, cfg) != EpistemicStatus.TRACKED:
        # CONTRACT-GAP: 15 says a non-TRACKED carrier requires reset, full stop. With zero
        # perception (PROTOCOL_ONLY, ADR-0011) nothing is ever TRACKED, so that reading makes
        # the Tier 0 checklist unsatisfiable and contradicts 03 D / 37 beat 4 ("the worker
        # resolves live"). The protocol question is asked instead: has this carrier had a valid
        # reset since this ticket was bound? A reset clears taint (13), so anything acquired
        # afterwards re-blocks via the taint check above. Each new bind asks again, which is
        # exactly "Tier 0 on every restricted bind" (10).
        return not reset_since(state, carrier.carrier_id, since)
    return False


def blocking_carriers(
    state: WorldState,
    carriers: list[str],
    restricted: frozenset[str],
    cfg: Config,
    since: int | None = None,
) -> list[str]:
    if not restricted:
        return []
    station = state.station
    return [
        cid
        for cid in carriers
        if cid in station.carriers
        and needs_reset(state, station.carriers[cid], restricted, cfg, since)
    ]


def check_preconditions(state: WorldState, ticket: Ticket, k: Knowledge, cfg: Config) -> list[str]:
    """Carriers requiring reset before this ticket may proceed; empty = preconditions met."""
    kp = KnowledgeProvider(k)
    restricted = restricted_allergens(ticket, kp)
    if not restricted:
        return []
    return blocking_carriers(
        state, required_carriers(state, ticket, kp), restricted, cfg, ticket.bound_at
    )
