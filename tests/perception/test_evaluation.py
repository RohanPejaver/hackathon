"""Scorer semantics (34 §Secondary — perception): hand-built annotations against hand-built
emitted payloads. No pipeline, no frames — `src.perception.evaluation` is pure."""

from __future__ import annotations

from typing import Any

import pytest

from src.perception.annotation import (
    AnnotatedEvent,
    OcclusionInterval,
    VideoAnnotation,
    load_annotation,
)
from src.perception.evaluation import (
    ClipScore,
    TypeScore,
    aggregate,
    clip_score,
    match_events,
    nuisance_rate,
    occlusion_recall,
)


def _emit(kind: str, t: int, **fields: Any) -> dict[str, Any]:
    return {
        "type": kind,
        "event_id": f"p:{kind}:{t}",
        "t_occurred": t,
        "station_id": "demo-bagel",
        "source": "PERCEPTION",
        "confidence": 0.9,
        "grade": "OBSERVED",
        "evidence": {"track_ids": [], "zone_ids": [], "frame_range": None},
        **fields,
    }


def _entry(t: int, carrier: str = "gloves", zone: str = "bin:pesto") -> AnnotatedEvent:
    return AnnotatedEvent(t_ms=t, type="ZONE_ENTRY", participants=[carrier], zone_id=zone)


def test_true_positive_within_tolerance() -> None:
    scores = match_events(
        [_entry(1000)], [_emit("ZONE_ENTRY", 1400, carrier="gloves", zone="bin:pesto")]
    )
    assert scores == {"ZONE_ENTRY": TypeScore(tp=1, fp=0, fn=0)}
    assert scores["ZONE_ENTRY"].precision == 1.0 and scores["ZONE_ENTRY"].recall == 1.0


def test_miss_outside_tolerance_is_fn_and_fp() -> None:
    scores = match_events(
        [_entry(1000)], [_emit("ZONE_ENTRY", 1600, carrier="gloves", zone="bin:pesto")]
    )
    assert scores == {"ZONE_ENTRY": TypeScore(tp=0, fp=1, fn=1)}
    assert scores["ZONE_ENTRY"].recall == 0.0


def test_participant_mismatch_is_fp_plus_fn() -> None:
    scores = match_events(
        [_entry(1000)], [_emit("ZONE_ENTRY", 1000, carrier="gloves", zone="bin:mayo")]
    )
    assert scores == {"ZONE_ENTRY": TypeScore(tp=0, fp=1, fn=1)}


def test_zone_may_be_given_as_participant_instead_of_zone_id() -> None:
    ann = AnnotatedEvent(t_ms=0, type="ZONE_EXIT", participants=["gloves", "bin:pesto"])
    scores = match_events([ann], [_emit("ZONE_EXIT", 100, carrier="gloves", zone="bin:pesto")])
    assert scores["ZONE_EXIT"].tp == 1


def test_contact_match_is_order_insensitive() -> None:
    ann = AnnotatedEvent(t_ms=5000, type="CONTACT_BEGIN", participants=["spreader", "gloves"])
    scores = match_events([ann], [_emit("CONTACT_BEGIN", 5200, a="gloves", b="spreader")])
    assert scores == {"CONTACT_BEGIN": TypeScore(tp=1, fp=0, fn=0)}


def test_swap_matches_on_retired_and_introduced() -> None:
    ann = AnnotatedEvent(t_ms=0, type="TOOL_SWAP", participants=["spreader", "spreader_2"])
    ok = _emit("TOOL_SWAP", 0, retired="spreader", introduced="spreader_2", from_zone="clean_stock")
    bad = _emit(
        "TOOL_SWAP", 0, retired="spreader", introduced="spreader_3", from_zone="clean_stock"
    )
    assert match_events([ann], [ok])["TOOL_SWAP"].tp == 1
    assert match_events([ann], [bad])["TOOL_SWAP"] == TypeScore(tp=0, fp=1, fn=1)


def test_glove_change_ignores_participants() -> None:
    ann = AnnotatedEvent(t_ms=12000, type="GLOVE_CHANGE", participants=["gloves"])
    scores = match_events([ann], [_emit("GLOVE_CHANGE", 12300, worker_slot=0, phase="DON")])
    assert scores["GLOVE_CHANGE"].tp == 1


def test_matching_is_one_to_one_and_prefers_the_closest() -> None:
    annotated = [_entry(1000), _entry(3000)]
    emitted = [
        _emit("ZONE_ENTRY", 1100, carrier="gloves", zone="bin:pesto"),
        _emit("ZONE_ENTRY", 1300, carrier="gloves", zone="bin:pesto"),  # duplicate -> FP
        _emit("ZONE_ENTRY", 2900, carrier="gloves", zone="bin:pesto"),
    ]
    assert match_events(annotated, emitted) == {"ZONE_ENTRY": TypeScore(tp=2, fp=1, fn=0)}


def test_unannotated_types_are_not_false_positives() -> None:
    emitted = [
        _emit("ZONE_ENTRY", 1000, carrier="gloves", zone="bin:pesto"),
        _emit(
            "CARRIER_OBSERVABILITY_CHANGED", 0, carrier="gloves", epistemic="TRACKED", cause="hb"
        ),
        _emit(
            "CARRIER_OBSERVABILITY_CHANGED", 9000, carrier="board", epistemic="TRACKED", cause="hb"
        ),
        _emit("HEALTH_DEGRADED", 100, cause="static frames"),
        _emit("ZONE_EXIT", 4000, carrier="gloves", zone="bin:pesto"),
    ]
    scores = match_events([_entry(1000)], emitted)
    assert set(scores) == {"ZONE_ENTRY"}
    assert scores["ZONE_ENTRY"] == TypeScore(tp=1, fp=0, fn=0)


def test_occlusion_recall_counts_only_unknown_reports_in_window() -> None:
    intervals = [
        OcclusionInterval(carrier_id="gloves", t_start=3000, t_end=8000),
        OcclusionInterval(carrier_id="spreader", t_start=10000, t_end=15000),
    ]
    emitted = [
        _emit(
            "CARRIER_OBSERVABILITY_CHANGED",
            6000,
            carrier="gloves",
            epistemic="UNKNOWN",
            cause="lost",
        ),
        # spreader only ever re-observed, never reported UNKNOWN -> that interval is missed
        _emit(
            "CARRIER_OBSERVABILITY_CHANGED",
            12000,
            carrier="spreader",
            epistemic="TRACKED",
            cause="hb",
        ),
    ]
    assert occlusion_recall(intervals, emitted) == (0.5, 1, 2)


def test_occlusion_recall_tolerance_edges() -> None:
    iv = [OcclusionInterval(carrier_id="gloves", t_start=3000, t_end=4000)]
    early = _emit(
        "CARRIER_OBSERVABILITY_CHANGED", 2000, carrier="gloves", epistemic="UNKNOWN", cause="x"
    )
    late = _emit(
        "CARRIER_OBSERVABILITY_CHANGED", 5001, carrier="gloves", epistemic="UNKNOWN", cause="x"
    )
    assert occlusion_recall(iv, [early]) == (1.0, 1, 1)
    assert occlusion_recall(iv, [late]) == (0.0, 0, 1)
    assert occlusion_recall([], [early]) == (0.0, 0, 0)


def test_clip_score_and_aggregate_micro_average() -> None:
    a = VideoAnnotation(
        clip_id="a",
        station_config_version=1,
        events=[_entry(1000), _entry(5000, zone="bin:mayo")],
        occlusion_intervals=[OcclusionInterval(carrier_id="gloves", t_start=6000, t_end=9000)],
        hazard_label="NONE",
    )
    b = VideoAnnotation(
        clip_id="b",
        station_config_version=1,
        events=[_entry(1000)],
        occlusion_intervals=[],
        hazard_label="DIRECT",
    )
    sa = clip_score(
        a,
        [
            _emit("ZONE_ENTRY", 1000, carrier="gloves", zone="bin:pesto"),
            _emit(
                "CARRIER_OBSERVABILITY_CHANGED",
                8000,
                carrier="gloves",
                epistemic="UNKNOWN",
                cause="lost",
            ),
        ],
    )
    sb = clip_score(b, [_emit("ZONE_ENTRY", 1000, carrier="gloves", zone="bin:mayo")])
    assert isinstance(sa, ClipScore)
    assert sa.by_type["ZONE_ENTRY"] == TypeScore(tp=1, fp=0, fn=1)
    assert sa.occlusion_recall == 1.0 and sa.occlusion_intervals == 1
    assert sb.by_type["ZONE_ENTRY"] == TypeScore(tp=0, fp=1, fn=1)
    assert sb.occlusion_recall is None  # nothing annotated -> not a number, not a free pass
    agg = aggregate([sa, sb])
    assert agg["by_type"]["ZONE_ENTRY"] == {
        "tp": 1,
        "fp": 1,
        "fn": 2,
        "precision": 0.5,
        "recall": 0.3333,
    }
    assert agg["occlusion_recall"] == 1.0 and agg["occlusion_intervals"] == 1
    assert agg["clips"] == 2
    assert sa.as_dict()["hazard_label"] == "NONE" and sb.as_dict()["emitted_total"] == 1


def test_nuisance_rate_per_hour() -> None:
    assert nuisance_rate(3, 5400) == 2.0
    assert nuisance_rate(0, 1800) == 0.0
    with pytest.raises(ValueError):
        nuisance_rate(1, 0)


def test_annotation_schema_is_strict(tmp_path: Any) -> None:
    good = tmp_path / "c.json"
    good.write_text(
        '{"clip_id": "c", "station_config_version": 1, "recorded_at": "2026-09-12T10:00:00",'
        ' "fps": 15, "events": [{"t_ms": 10, "type": "ZONE_ENTRY", "participants": ["gloves"],'
        ' "zone_id": "bin:pesto", "ground_truth": true}],'
        ' "occlusion_intervals": [{"carrier_id": "gloves", "t_start": 1, "t_end": 2}],'
        ' "hazard_label": "TOOL"}'
    )
    ann = load_annotation(good)
    assert ann.events[0].zone_id == "bin:pesto" and ann.hazard_label == "TOOL"
    bad = tmp_path / "bad.json"
    bad.write_text('{"clip_id": "c", "station_config_version": 1, "hazard_label": "MAYBE"}')
    with pytest.raises(ValueError):
        load_annotation(bad)
    with pytest.raises(ValueError):
        AnnotatedEvent(t_ms=0, type="ZONE_ENTRY", participants=[], ground_truth=False)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        OcclusionInterval(carrier_id="gloves", t_start=5, t_end=4)
