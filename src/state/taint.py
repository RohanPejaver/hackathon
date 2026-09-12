"""Taint acquisition and propagation (13 §Transition table, 14 §Pathway definition).

Taint never decays by time (13 §Expiry): the only way a record leaves a carrier is a valid
reset or the carrier leaving the active set. Propagation is bidirectional and symmetric
(13 §Why propagation is bidirectional), takes the minimum grade along the edge (13 §Grade
lattice), weakens strength per hop (14 §Parameters) and halts at `max_hops` (11 inv. 6).
"""

from __future__ import annotations

from src.domain import (
    GRADE_RANK,
    Carrier,
    Config,
    EvidenceGrade,
    Strength,
    TaintRecord,
    ZoneKind,
)

from ._draft import Draft


def min_grade(a: EvidenceGrade, b: EvidenceGrade) -> EvidenceGrade:
    return a if GRADE_RANK[a] <= GRADE_RANK[b] else b


def weaker(a: Strength, b: Strength) -> Strength:
    return Strength.POSSIBLE if Strength.POSSIBLE in (a, b) else Strength.PRESENT


def decay_for(cfg: Config, hops: int) -> Strength:
    ladder = cfg.strength_decay_per_hop
    if not ladder:
        return Strength.PRESENT
    return ladder[min(hops, len(ladder) - 1)]


def acquire_from_zone(draft: Draft, carrier_id: str, zone_id: str, grade: EvidenceGrade) -> None:
    """ZONE_ENTRY into an INGREDIENT zone: hop-0 acquisition of the zone's allergen profile."""
    zone = draft.zones[zone_id]
    if zone.kind != ZoneKind.INGREDIENT:
        return
    profile = draft.base.zone_allergens.get(zone_id, {})
    source = zone.bound_carrier or zone.zone_id
    for allergen in sorted(profile):
        record = TaintRecord(
            allergen_id=allergen,
            acquired_at=draft.t,
            source_event_id=draft.event_id,
            source_carrier_id=source,
            grade=grade,
            hops=0,
            strength=profile[allergen],
        )
        draft.put_taint("zone_acquire", carrier_id, record)
        before = draft.recent_allergen_exposure.get(allergen)
        if before != draft.t:
            draft.recent_allergen_exposure[allergen] = draft.t
            draft.delta(
                "zone_acquire", f"recent_allergen_exposure.{allergen}", before, draft.t, carrier_id
            )


def propagate(draft: Draft, a: str, b: str, grade: EvidenceGrade, cfg: Config) -> None:
    """One physical contact between carriers `a` and `b`: record the edge once and transfer
    taint in both directions from pre-contact snapshots."""
    if a == b:
        return
    snap_a, snap_b = draft.carriers[a], draft.carriers[b]
    draft.record_contact(a, b, grade)
    _transfer(draft, snap_a, snap_b, grade, cfg)
    _transfer(draft, snap_b, snap_a, grade, cfg)


def source_profile(draft: Draft, carrier_id: str) -> set[str]:
    """Allergens this carrier is a configured hop-0 source of (the bound container of an
    INGREDIENT zone). Propagating those *into* it would be a hop>=1 record on the source."""
    # CONTRACT-GAP: 13/14 do not say whether the pesto tub "acquires" PINE_NUT back from a
    # hand that just dipped in it. It is the source (zone_allergens), so such a record would
    # be false evidence of a transfer; the reducer skips it. Foreign allergens still land.
    profile: set[str] = set()
    for zone in draft.zones.values():
        if zone.kind == ZoneKind.INGREDIENT and zone.bound_carrier == carrier_id:
            profile |= set(draft.base.zone_allergens.get(zone.zone_id, {}))
    return profile


def _transfer(
    draft: Draft, source: Carrier, target: Carrier, grade: EvidenceGrade, cfg: Config
) -> None:
    own = source_profile(draft, target.carrier_id)
    for allergen in sorted(source.taints):
        r = source.taints[allergen]
        if r.hops >= cfg.max_hops or allergen in own:
            continue
        hops = r.hops + 1
        record = TaintRecord(
            allergen_id=allergen,
            acquired_at=draft.t,
            source_event_id=draft.event_id,
            source_carrier_id=source.carrier_id,
            grade=min_grade(r.grade, grade),
            hops=hops,
            strength=weaker(r.strength, decay_for(cfg, hops)),
        )
        draft.put_taint("contact_propagate", target.carrier_id, record)


def merge_identity(draft: Draft, a: str, b: str) -> None:
    """TRACK_IDENTITY_SUSPECT: both carriers hold the union; per allergen the record with
    fewer hops wins, then the higher grade, then `a`'s. Copies reference this event so the
    trace explains why the taint appeared (11 inv. 3)."""
    ca, cb = draft.carriers[a], draft.carriers[b]
    for allergen in sorted(set(ca.taints) | set(cb.taints)):
        ra, rb = ca.taints.get(allergen), cb.taints.get(allergen)
        if ra is not None and (rb is None or _rank(ra) <= _rank(rb)):
            winner, origin, receiver = ra, a, b
        elif rb is not None:
            winner, origin, receiver = rb, b, a
        else:
            continue
        copy = winner.model_copy(
            update={
                "acquired_at": draft.t,
                "source_event_id": draft.event_id,
                "source_carrier_id": origin,
            }
        )
        _force_taint(draft, receiver, copy)


def _rank(r: TaintRecord) -> tuple[int, int]:
    """Smaller is stronger evidence: fewer hops, then higher grade."""
    return (r.hops, -GRADE_RANK[r.grade])


def _force_taint(draft: Draft, carrier_id: str, record: TaintRecord) -> None:
    """Store the merged record unless the receiver already holds evidence at least as strong."""
    carrier = draft.carriers[carrier_id]
    existing = carrier.taints.get(record.allergen_id)
    if existing is not None and _rank(existing) <= _rank(record):
        return
    taints = dict(carrier.taints)
    taints[record.allergen_id] = record
    draft.carriers[carrier_id] = carrier.model_copy(update={"taints": taints})
    draft.delta(
        "identity_merge",
        f"taints.{record.allergen_id}",
        None if existing is None else existing.model_dump(mode="json"),
        record.model_dump(mode="json"),
        carrier_id=carrier_id,
    )
    draft.acquisitions.setdefault(carrier_id, []).append(record)
