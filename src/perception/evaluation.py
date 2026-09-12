"""Perception scoring (34 §Secondary — perception, §Nuisance Rate; 38 §P4 gate).

Pure functions over annotation models and emitted event payload dicts (the dicts
`PerceptionPipeline.process_frame` returns). Nothing here touches a clock, a file or a
frame; `scripts/eval_perception.py` does the I/O and writes the artifact.

Matching rule (event level, 35): an emitted event matches an annotated one iff
  * same `type`,
  * |t_occurred - t_ms| <= tolerance_ms, and
  * the participant set matches — ZONE_ENTRY/ZONE_EXIT: {carrier, zone}; CONTACT_*: {a, b}
    order-insensitive; GLOVE_CHANGE: participants ignored (worker_slot is not annotated);
    TOOL_SWAP/SURFACE_SWAP: {retired, introduced}; anything else: {carrier[, zone]}.
Matching is greedy one-to-one by smallest time gap. An unmatched emitted event of an
*annotated* type is a false positive; an unmatched annotated event is a false negative.
Emitted types the clip never annotates (the CARRIER_OBSERVABILITY_CHANGED heartbeat,
HEALTH_DEGRADED, ...) are excluded from FP counting: they are honesty/health traffic, not
detections under test.

Import scope: only `src.domain` / `src.events` are permitted (30 rule 2); neither is needed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .annotation import AnnotatedEvent, OcclusionInterval, VideoAnnotation

DEFAULT_EVENT_TOLERANCE_MS = 500
DEFAULT_OCCLUSION_TOLERANCE_MS = 1000

_ZONE_TYPES = frozenset({"ZONE_ENTRY", "ZONE_EXIT"})
_CONTACT_TYPES = frozenset({"CONTACT_BEGIN", "CONTACT_END", "TRACK_IDENTITY_SUSPECT"})
_SWAP_TYPES = frozenset({"TOOL_SWAP", "SURFACE_SWAP"})
_PARTICIPANT_FREE_TYPES = frozenset({"GLOVE_CHANGE"})


@dataclass(frozen=True)
class TypeScore:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float:
        n = self.tp + self.fp
        return self.tp / n if n else 0.0

    @property
    def recall(self) -> float:
        n = self.tp + self.fn
        return self.tp / n if n else 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
        }


@dataclass(frozen=True)
class ClipScore:
    clip_id: str
    by_type: dict[str, TypeScore]
    occlusion_recall: float | None  # None when the clip annotates no intervals
    occlusion_intervals: int
    occlusion_reported: int
    hazard_label: str
    emitted_total: int = 0
    emitted_by_type: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "by_type": {k: v.as_dict() for k, v in sorted(self.by_type.items())},
            "occlusion_recall": self.occlusion_recall,
            "occlusion_intervals": self.occlusion_intervals,
            "occlusion_reported": self.occlusion_reported,
            "hazard_label": self.hazard_label,
            "emitted_total": self.emitted_total,
            "emitted_by_type": dict(sorted(self.emitted_by_type.items())),
        }


# ---- participant sets --------------------------------------------------------------------------


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def annotated_participants(event: AnnotatedEvent) -> frozenset[str]:
    ids = set(event.participants)
    if event.zone_id is not None:
        ids.add(event.zone_id)
    return frozenset(ids)


def emitted_participants(event: Mapping[str, Any]) -> frozenset[str]:
    kind = _str(event.get("type")) or ""
    if kind in _ZONE_TYPES:
        keys: tuple[str, ...] = ("carrier", "zone")
    elif kind in _CONTACT_TYPES:
        keys = ("a", "b")
    elif kind in _SWAP_TYPES:
        keys = ("retired", "introduced")
    else:
        keys = ("carrier", "zone")
    return frozenset(v for k in keys if (v := _str(event.get(k))) is not None)


def participants_match(annotated: AnnotatedEvent, emitted: Mapping[str, Any]) -> bool:
    if annotated.type in _PARTICIPANT_FREE_TYPES:
        return True
    return annotated_participants(annotated) == emitted_participants(emitted)


def _t_occurred(event: Mapping[str, Any]) -> int | None:
    t = event.get("t_occurred")
    return t if isinstance(t, int) and not isinstance(t, bool) else None


# ---- event-level precision / recall -------------------------------------------------------------


def match_events(
    annotated: Sequence[AnnotatedEvent],
    emitted: Sequence[Mapping[str, Any]],
    tolerance_ms: int = DEFAULT_EVENT_TOLERANCE_MS,
) -> dict[str, TypeScore]:
    """Per-type tp/fp/fn. Only types present in `annotated` appear in the result."""
    annotated_types = {a.type for a in annotated}
    candidates: list[tuple[int, int, int]] = []
    for ai, a in enumerate(annotated):
        for ei, e in enumerate(emitted):
            if _str(e.get("type")) != a.type:
                continue
            t = _t_occurred(e)
            if t is None or abs(t - a.t_ms) > tolerance_ms:
                continue
            if participants_match(a, e):
                candidates.append((abs(t - a.t_ms), ai, ei))
    candidates.sort()
    matched_a: set[int] = set()
    matched_e: set[int] = set()
    for _, ai, ei in candidates:
        if ai in matched_a or ei in matched_e:
            continue
        matched_a.add(ai)
        matched_e.add(ei)

    tp: dict[str, int] = dict.fromkeys(annotated_types, 0)
    fp: dict[str, int] = dict.fromkeys(annotated_types, 0)
    fn: dict[str, int] = dict.fromkeys(annotated_types, 0)
    for ai, a in enumerate(annotated):
        if ai in matched_a:
            tp[a.type] += 1
        else:
            fn[a.type] += 1
    for ei, e in enumerate(emitted):
        kind = _str(e.get("type"))
        if kind in annotated_types and ei not in matched_e:
            fp[kind] += 1
    return {k: TypeScore(tp=tp[k], fp=fp[k], fn=fn[k]) for k in sorted(annotated_types)}


# ---- occlusion-reporting recall ---------------------------------------------------------------


def occlusion_recall(
    intervals: Sequence[OcclusionInterval],
    emitted: Sequence[Mapping[str, Any]],
    tolerance_ms: int = DEFAULT_OCCLUSION_TOLERANCE_MS,
) -> tuple[float, int, int]:
    """(fraction, reported, total): an interval counts as reported when a
    CARRIER_OBSERVABILITY_CHANGED for its carrier with epistemic UNKNOWN has t_occurred in
    [t_start - tolerance, t_end + tolerance]. Empty input yields (0.0, 0, 0)."""
    unknowns: list[tuple[str, int]] = []
    for e in emitted:
        if _str(e.get("type")) != "CARRIER_OBSERVABILITY_CHANGED":
            continue
        epistemic = e.get("epistemic")
        if str(getattr(epistemic, "value", epistemic)) != "UNKNOWN":
            continue
        carrier = _str(e.get("carrier"))
        t = _t_occurred(e)
        if carrier is not None and t is not None:
            unknowns.append((carrier, t))
    reported = 0
    for iv in intervals:
        lo, hi = iv.t_start - tolerance_ms, iv.t_end + tolerance_ms
        if any(c == iv.carrier_id and lo <= t <= hi for c, t in unknowns):
            reported += 1
    total = len(intervals)
    return (reported / total if total else 0.0), reported, total


# ---- per clip and aggregate ----------------------------------------------------------------


def clip_score(
    annotation: VideoAnnotation,
    emitted: Sequence[Mapping[str, Any]],
    *,
    tolerance_ms: int = DEFAULT_EVENT_TOLERANCE_MS,
    occlusion_tolerance_ms: int = DEFAULT_OCCLUSION_TOLERANCE_MS,
) -> ClipScore:
    fraction, reported, total = occlusion_recall(
        annotation.occlusion_intervals, emitted, occlusion_tolerance_ms
    )
    counts: dict[str, int] = {}
    for e in emitted:
        kind = _str(e.get("type")) or "?"
        counts[kind] = counts.get(kind, 0) + 1
    return ClipScore(
        clip_id=annotation.clip_id,
        by_type=match_events(annotation.events, emitted, tolerance_ms),
        occlusion_recall=fraction if total else None,
        occlusion_intervals=total,
        occlusion_reported=reported,
        hazard_label=annotation.hazard_label,
        emitted_total=len(emitted),
        emitted_by_type=counts,
    )


def aggregate(scores: Iterable[ClipScore]) -> dict[str, Any]:
    """Micro-averaged precision/recall per type across clips, plus overall occlusion recall
    (reported intervals / annotated intervals; None when nothing was annotated)."""
    tp: dict[str, int] = {}
    fp: dict[str, int] = {}
    fn: dict[str, int] = {}
    reported = total = 0
    clips = 0
    for s in scores:
        clips += 1
        reported += s.occlusion_reported
        total += s.occlusion_intervals
        for kind, ts in s.by_type.items():
            tp[kind] = tp.get(kind, 0) + ts.tp
            fp[kind] = fp.get(kind, 0) + ts.fp
            fn[kind] = fn.get(kind, 0) + ts.fn
    by_type = {k: TypeScore(tp=tp[k], fp=fp[k], fn=fn[k]).as_dict() for k in sorted(tp)}
    return {
        "clips": clips,
        "by_type": by_type,
        "occlusion_intervals": total,
        "occlusion_reported": reported,
        "occlusion_recall": (reported / total) if total else None,
    }


def nuisance_rate(tier12_raises: int, duration_s: float) -> float:
    """Tier 1 + Tier 2 alerts per hour of normal prep (34 §3). Tier 0 is excluded by
    definition and must not be passed in."""
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    return tier12_raises * 3600.0 / duration_s
