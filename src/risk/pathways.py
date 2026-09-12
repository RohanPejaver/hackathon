"""Bounded backward pathway search over the temporal contact graph (14, 15 §2, 39 §4)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain import (
    GRADE_RANK,
    CarrierKind,
    Config,
    ContactEdge,
    EvidenceGrade,
    Pathway,
    ResetRecord,
    Strength,
    WorldState,
)
from src.knowledge import matches


@dataclass(frozen=True)
class _Frontier:
    carrier: str
    t_upper: int | None  # None = +inf (the target has no outbound contact)
    edges: tuple[ContactEdge, ...]  # reverse chronological
    nodes: tuple[str, ...]  # target first, current last
    broken: bool


def breaks(reset: ResetRecord, t_in: int, t_out: int | None) -> bool:
    """Does `reset` on a node break the chain between its inbound and outbound contacts?

    14 rule 3: a valid reset strictly between the two contacts. An OPERATOR_ASSERTION is a
    human vouching for the carrier as used, so it breaks the chain at any time after the
    inbound contact (product/03 scenario D; 26 §Handling false alerts).
    """
    if reset.t_occurred <= t_in:
        return False
    return reset.operator or t_out is None or reset.t_occurred < t_out


def _min_grade(grades: list[EvidenceGrade]) -> EvidenceGrade:
    return min(grades, key=lambda g: GRADE_RANK[g])


def _index_edges(state: WorldState) -> dict[str, list[ContactEdge]]:
    by: dict[str, list[ContactEdge]] = {}
    for e in state.contacts:
        by.setdefault(e.a, []).append(e)
        if e.b != e.a:
            by.setdefault(e.b, []).append(e)
    for edges in by.values():
        edges.sort(key=lambda e: (-e.t_occurred, e.event_id))
    return by


def _index_resets(state: WorldState) -> dict[str, list[ResetRecord]]:
    by: dict[str, list[ResetRecord]] = {}
    for r in state.resets:
        by.setdefault(r.carrier_id, []).append(r)
    return by


def _stronger(a: Strength | None, b: Strength) -> Strength:
    return Strength.PRESENT if Strength.PRESENT in (a, b) else Strength.POSSIBLE


def _zone_sources(state: WorldState, allergens: frozenset[str]) -> dict[str, dict[str, Strength]]:
    """Carriers bound to an ingredient zone whose profile intersects `allergens`."""
    out: dict[str, dict[str, Strength]] = {}
    for zone in state.station.zones.values():
        if zone.bound_carrier is None:
            continue
        for a, strength in state.zone_allergens.get(zone.zone_id, {}).items():
            if matches(a, allergens):
                profile = out.setdefault(zone.bound_carrier, {})
                profile[a] = _stronger(profile.get(a), strength)
    return out


def _container_sources(
    state: WorldState,
    resets: dict[str, list[ResetRecord]],
    carrier_id: str,
    t_edge: int,
    allergens: frozenset[str],
) -> dict[str, Strength]:
    """14 §Back-contamination: a CONTAINER that acquired a matching taint before `t_edge`,
    with no reset on it since, is a source for every later pathway."""
    carrier = state.station.carriers.get(carrier_id)
    if carrier is None or carrier.kind != CarrierKind.CONTAINER:
        return {}
    out: dict[str, Strength] = {}
    for rec in state.acquisitions.get(carrier_id, []):
        if rec.acquired_at >= t_edge or not matches(rec.allergen_id, allergens):
            continue
        if any(breaks(r, rec.acquired_at, t_edge) for r in resets.get(carrier_id, [])):
            continue
        out[rec.allergen_id] = _stronger(out.get(rec.allergen_id), rec.strength)
    return out


def _strength(source: Strength, hops: int, cfg: Config) -> Strength:
    if source == Strength.POSSIBLE or not cfg.strength_decay_per_hop:
        return source
    decay = cfg.strength_decay_per_hop
    return decay[min(hops, len(decay) - 1)]


def _pathway(
    allergen: str,
    strength: Strength,
    source: str,
    frontier: _Frontier,
    edges: tuple[ContactEdge, ...],
    broken: bool,
    cfg: Config,
) -> Pathway:
    hops = len(edges) - 1
    return Pathway(
        allergen_id=allergen,
        nodes=[source, *reversed(frontier.nodes)],
        event_ids=[e.event_id for e in reversed(edges)],
        grade=_min_grade([e.grade for e in edges]),
        hops=hops,
        broken=broken,
        strength=_strength(strength, hops, cfg),
    )


def find_pathways(
    state: WorldState, target: str, allergens: frozenset[str], cfg: Config
) -> list[Pathway]:
    """Backward BFS from `target`: strictly decreasing contact times, at most `max_hops`
    edges, never revisiting a carrier. A reset between a node's inbound and outbound
    contacts marks the pathway broken but it is still reported (16: resolution is shown,
    not silently cleared). Results are sorted by (broken, hops, nodes, allergen)."""
    if not allergens:
        return []
    edges_by = _index_edges(state)
    resets_by = _index_resets(state)
    zone_sources = _zone_sources(state, allergens)
    found: list[Pathway] = []
    seen: set[tuple[str, tuple[str, ...], bool]] = set()
    frontier = [_Frontier(target, None, (), (target,), False)]
    for _ in range(cfg.max_hops):
        next_frontier: list[_Frontier] = []
        for f in frontier:
            for e in edges_by.get(f.carrier, []):
                if f.t_upper is not None and e.t_occurred >= f.t_upper:
                    continue
                other = e.b if e.a == f.carrier else e.a
                if other in f.nodes:
                    continue
                broken = f.broken or any(
                    breaks(r, e.t_occurred, f.t_upper) for r in resets_by.get(f.carrier, [])
                )
                edges = (*f.edges, e)
                sources = dict(zone_sources.get(other, {}))
                for a, s in _container_sources(
                    state, resets_by, other, e.t_occurred, allergens
                ).items():
                    sources[a] = _stronger(sources.get(a), s)
                if sources:
                    for a, s in sorted(sources.items()):
                        p = _pathway(a, s, other, f, edges, broken, cfg)
                        ident = (a, tuple(p.nodes), broken)
                        if ident not in seen:
                            seen.add(ident)
                            found.append(p)
                else:
                    next_frontier.append(
                        _Frontier(other, e.t_occurred, edges, (*f.nodes, other), broken)
                    )
        frontier = next_frontier
        if not frontier:
            break
    found.sort(key=lambda p: (p.broken, p.hops, p.nodes, p.allergen_id))
    return found


def breaking_resets(state: WorldState, pathway: Pathway) -> list[ResetRecord]:
    """The resets that break `pathway`, chronologically; empty for an open pathway."""
    times = {e.event_id: e.t_occurred for e in state.contacts}
    out: list[ResetRecord] = []
    for i in range(1, len(pathway.nodes)):
        node = pathway.nodes[i]
        t_in = times.get(pathway.event_ids[i - 1])
        if t_in is None:
            continue
        t_out = times.get(pathway.event_ids[i]) if i < len(pathway.event_ids) else None
        out.extend(r for r in state.resets if r.carrier_id == node and breaks(r, t_in, t_out))
    out.sort(key=lambda r: (r.t_occurred, r.event_id))
    return out
