#!/usr/bin/env python
"""P4 gate artifact (38 §P4, 34 §Secondary — perception, §Nuisance Rate, §Acceptance).

    python scripts/eval_perception.py [--videos data/fixtures/video] [--normal data/fixtures/normal]
                                      [--date YYYY-MM-DD] [--out-dir data/eval] [--synthetic]

Runs the perception pipeline offline (`PerceptionPipeline.process_frame`, one frame at a time,
no threads, `t_ms = frame_index * 1000 // fps`) over every `<clip>.mp4` that has a
`<clip>.json` annotation (35), scores it at the event level, then runs the normal-prep set
and folds its emitted events through the reasoning core exactly as `src/replay/runner.py`
does to count Tier 1/2 raises per hour. Writes `data/eval/<date>/p4_perception_report.json`
and exits 1 when the gate is not met or no clips exist.

`--synthetic` renders three short clips with `tests/perception/synth.py` (imported by
inserting the repo root on sys.path; nothing is duplicated) under a temp dir, with
annotations derived from the same motions, and scores them: this proves the scorer end to
end without a camera and is what the test runs. Such a report carries `"synthetic": true`
and is not evidence for the P4 gate.

Nuisance fold caveat: Tier 1/2 needs a bound ticket with a restriction (16), and normal prep
carries no ticket. One synthetic restricted ticket ("T-nuisance": turkey_sandwich, "pine nut
allergy") is therefore bound at t=0 of every normal clip so that a nuisance alert *can*
occur. The report says so.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain import Config, Knowledge, Mode, StationConfig, Ticket, TicketLifecycle  # noqa: E402
from src.events import EVENT_ADAPTER, project  # noqa: E402
from src.orders import intake  # noqa: E402
from src.perception.annotation import VideoAnnotation, load_annotation  # noqa: E402
from src.perception.config import PerceptionConfig  # noqa: E402
from src.perception.evaluation import ClipScore, aggregate, clip_score, nuisance_rate  # noqa: E402
from src.perception.pipeline import PerceptionPipeline  # noqa: E402
from src.policy import AlertState, evaluate  # noqa: E402
from src.risk import assess  # noqa: E402
from src.runtime.config import ConfigError, LoadedConfig, load, to_domain  # noqa: E402
from src.state import initial, reduce  # noqa: E402

TARGET_OCCLUSION_RECALL = 0.95
TARGET_NUISANCE_PER_HOUR = 1.0
# CONTRACT-GAP: 34 fixes no per-type precision/recall number ("meets targets" in 38 §P4 is
# not quantified). 0.8 recall per annotated type is this driver's default and is reported
# as such.
DEFAULT_TYPE_RECALL = 0.8
NUISANCE_TICKET = ("T-nuisance", "turkey_sandwich", "pine nut allergy")
_LIVE = frozenset(
    {TicketLifecycle.BOUND, TicketLifecycle.IN_PREP, TicketLifecycle.COMPLETE, TicketLifecycle.HELD}
)


# ---- configuration -------------------------------------------------------------------------------


def perception_config(loaded: LoadedConfig, camera_source: int | str) -> PerceptionConfig:
    """Build the pipeline config from the loaded YAML exactly as the runtime does; offline."""
    v = loaded.values
    p = v.perception
    cal = loaded.station.calibration
    return PerceptionConfig.build(
        station_id=loaded.station.station_id,
        width_mm=cal.width_mm,
        height_mm=cal.height_mm,
        homography=cal.homography,  # None -> the pipeline self-calibrates from the corners
        fps=v.capture.fps,
        t_dwell_ms=v.temporal.t_dwell_ms,
        t_hysteresis_ms=v.temporal.t_hysteresis_ms,
        t_occlusion_max_ms=v.temporal.t_occlusion_max_s * 1000,
        heartbeat_ms=min(v.temporal.t_stale_s.values()) * 500,
        threshold_observed={k: t.observed for k, t in p.thresholds.items()},
        threshold_inferred={k: t.inferred for k, t in p.thresholds.items()},
        camera_source=camera_source,
        marker_dictionary=p.markers.dictionary,
        corner_ids=tuple(p.markers.corner_ids),
        corner_size_mm=p.markers.corner_size_mm,
        tool_size_mm=p.markers.tool_size_mm,
        hsv_lower=p.gloves.hsv_lower,
        hsv_upper=p.gloves.hsv_upper,
        min_area_px=p.gloves.min_area_px,
        glove_change_absence_ms=int(p.glove_change_absence_s * 1000),
        frame_timeout_ms=int(p.health.frame_timeout_s * 1000),
        static_frames=p.health.static_frames,
        frame_rate_floor_fps=p.frame_rate_floor_fps,
        tool_markers=dict(loaded.station.markers.tools),
        surface_markers=dict(loaded.station.markers.surfaces),
        realtime=False,
    )


# ---- offline pipeline run ------------------------------------------------------------------------


def _frames(path: Path) -> Iterator[np.ndarray]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                return
            yield np.asarray(frame, dtype=np.uint8)
    finally:
        cap.release()


def video_fps(path: Path, fallback: int) -> int:
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 0.0
    finally:
        cap.release()
    return int(round(fps)) if fps and fps > 0 else fallback


def run_clip(
    loaded: LoadedConfig, station: StationConfig, path: Path, fps: int
) -> tuple[list[dict[str, Any]], int]:
    """Every payload the pipeline emits for the clip, and the frame count."""
    pipe = PerceptionPipeline()
    pipe.configure(perception_config(loaded, str(path)), station)
    emitted: list[dict[str, Any]] = []
    frames = 0
    for i, frame in enumerate(_frames(path)):
        frames += 1
        emitted.extend(pipe.process_frame(frame, i * 1000 // fps))
    return emitted, frames


# ---- nuisance fold (the runtime's fold, as src/replay/runner.py runs it) --------------------


class NuisanceFold:
    """initial -> per event: commit envelope -> project -> reduce -> alerts.observe ->
    (mutates_state) assess live tickets -> evaluate -> count RAISE/ESCALATE by tier."""

    def __init__(self, cfg: Config, station: StationConfig, k: Knowledge) -> None:
        self.cfg = cfg
        self.k = k
        self.state = initial(cfg, station.model_copy(update={"mode": Mode.REPLAY}))
        self.alerts = AlertState(cfg)
        self.seq = 0
        self.tier0 = 0
        self.tier12 = 0
        self.raises: list[dict[str, Any]] = []

    def commit(self, payload: dict[str, Any], t: int) -> Any:
        data: dict[str, Any] = {
            **payload,
            "seq": self.seq,
            "t_committed": t,
            "station_id": self.state.station.station_id,
        }
        data.setdefault("event_id", f"nuisance:{self.seq:04d}")
        data.setdefault("t_occurred", t)
        event = EVENT_ADAPTER.validate_python(data)
        self.seq += 1
        graded = project(event)
        self.state, _ = reduce(self.state, graded, self.cfg)
        self.alerts.observe(graded)
        if graded.mutates_state:
            self._assess(event.event_id)
        return event

    def _assess(self, cause_event_id: str) -> None:
        live: list[Ticket] = sorted(
            (tk for tk in self.state.tickets.values() if tk.lifecycle in _LIVE),
            key=lambda tk: tk.ticket_id,
        )
        assessments = assess(self.state, live, self.k, self.cfg)
        for cmd in evaluate(assessments, self.alerts, self.cfg):
            alert = self.alerts.apply(cmd)
            if cmd.kind not in ("RAISE", "ESCALATE"):
                continue
            tier = int(alert.tier)
            if tier >= 1:
                self.tier12 += 1
                self.raises.append(
                    {
                        "t": cmd.t_occurred,
                        "kind": cmd.kind,
                        "tier": tier,
                        "headline": alert.headline,
                        "cause_event_id": cause_event_id,
                    }
                )
            else:
                self.tier0 += 1
            ticket = self.state.tickets.get(alert.ticket_id)
            if tier == 2 and ticket is not None and ticket.lifecycle != TicketLifecycle.HELD:
                self.commit(
                    {
                        "type": "TICKET_HELD",
                        "source": "SYSTEM",
                        "grade": "OBSERVED",
                        "ticket": alert.ticket_id,
                        "alert_id": alert.alert_id,
                    },
                    cmd.t_occurred,
                )

    def bind_synthetic_ticket(self) -> None:
        ticket_id, item, note = NUISANCE_TICKET
        received = self.commit(
            {
                "type": "TICKET_RECEIVED",
                "source": "ORDER_SYSTEM",
                "grade": "OBSERVED",
                "ticket": ticket_id,
                "items": [item],
                "restrictions": [{"raw_text": note}],
                "order_source": "eval",
            },
            0,
        )
        for draft in intake(
            ticket_id,
            [note],
            self.k,
            t=0,
            station_id=self.state.station.station_id,
            event_id_prefix=received.event_id,
        ):
            self.commit(draft.model_dump(), 0)
        self.commit(
            {
                "type": "TICKET_BOUND",
                "source": "OPERATOR",
                "grade": "OBSERVED",
                "ticket": ticket_id,
                "worker_slot": 0,
            },
            0,
        )
        self.commit(
            {
                "type": "TICKET_PREP_STARTED",
                "source": "OPERATOR",
                "grade": "OBSERVED",
                "ticket": ticket_id,
            },
            0,
        )


def fold_normal_clip(
    cfg: Config, station: StationConfig, k: Knowledge, emitted: list[dict[str, Any]]
) -> NuisanceFold:
    fold = NuisanceFold(cfg, station, k)
    fold.bind_synthetic_ticket()
    for payload in sorted(emitted, key=lambda p: (int(p["t_occurred"]), str(p["event_id"]))):
        fold.commit(payload, int(payload["t_occurred"]))
    return fold


# ---- synthetic clips ---------------------------------------------------------------------------


def render_synthetic(directory: Path, fps: int) -> tuple[Path, Path]:
    """Three clips whose motions the pipeline's own rules make deterministic. Returns the
    (videos, normal) directories."""
    from tests.perception.synth import mm_to_px, render_frame, write_video

    videos = directory / "video"
    normal = directory / "normal"
    videos.mkdir(parents=True)
    normal.mkdir(parents=True)
    step = 1000 // fps

    def t_at(frame: int) -> int:
        return frame * 1000 // fps

    def first_frame_at_or_after(ms: int) -> int:
        return -(-ms * fps // 1000)  # ceil

    # Clip 1: glove inside bin:pesto from frame 0, then gone for the rest of the clip.
    # ZONE_ENTRY once the dwell is met, ZONE_EXIT after the hysteresis, UNKNOWN after
    # t_occlusion_max (3 s) of absence.
    seconds = 8
    vanish = first_frame_at_or_after(3000)
    frames = [
        render_frame(glove_px=mm_to_px((170.0, 470.0)) if i < vanish else None)
        for i in range(seconds * fps)
    ]
    write_video(videos / "synthetic-zone-occlusion.mp4", frames, fps)
    entry_t = t_at(first_frame_at_or_after(250))  # dwell t_dwell_ms = 250
    exit_t = t_at(vanish + first_frame_at_or_after(400))  # hysteresis 400 ms after absence
    _write_annotation(
        videos / "synthetic-zone-occlusion.json",
        "synthetic-zone-occlusion",
        fps,
        events=[
            {
                "t_ms": entry_t,
                "type": "ZONE_ENTRY",
                "participants": ["gloves"],
                "zone_id": "bin:pesto",
                "ground_truth": True,
            },
            {
                "t_ms": exit_t,
                "type": "ZONE_EXIT",
                "participants": ["gloves"],
                "zone_id": "bin:pesto",
                "ground_truth": True,
            },
        ],
        occlusion=[
            {"carrier_id": "gloves", "t_start": t_at(vanish), "t_end": t_at(seconds * fps - 1)}
        ],
        hazard="NONE",
    )

    # Clip 2: marker 10 (spreader) in the zone-free front strip; the glove appears beside it
    # (circle overlap, 20 §Contact predicate) for ~3 s, then leaves. CONTACT_BEGIN/END.
    seconds = 6
    appear = first_frame_at_or_after(1000)
    leave = first_frame_at_or_after(4000)
    marker = {10: mm_to_px((500.0, 30.0))}
    glove = mm_to_px((604.0, 30.0))
    frames = [
        render_frame(markers_px=marker, glove_px=glove if appear <= i < leave else None)
        for i in range(seconds * fps)
    ]
    write_video(videos / "synthetic-contact.mp4", frames, fps)
    begin_t = t_at(appear + first_frame_at_or_after(250))
    end_t = t_at(leave + first_frame_at_or_after(400))
    _write_annotation(
        videos / "synthetic-contact.json",
        "synthetic-contact",
        fps,
        events=[
            {
                "t_ms": begin_t,
                "type": "CONTACT_BEGIN",
                "participants": ["spreader", "gloves"],
                "ground_truth": True,
            },
            {
                "t_ms": end_t,
                "type": "CONTACT_END",
                "participants": ["gloves", "spreader"],
                "ground_truth": True,
            },
        ],
        occlusion=[],
        hazard="TOOL",
    )

    # Normal clip: hazard-free prep for a pine-nut-restricted turkey sandwich — the glove
    # dips into bin:turkey, then bin:bread, then rests on the work surface. Never pesto.
    seconds = 12
    plan = [((690.0, 470.0), 4), ((950.0, 470.0), 4), ((500.0, 190.0), 4)]
    frames = []
    for pos, secs in plan:
        frames += [render_frame(glove_px=mm_to_px(pos)) for _ in range(secs * fps)]
    write_video(normal / "synthetic-normal.mp4", frames, fps)
    _write_annotation(normal / "synthetic-normal.json", "synthetic-normal", fps, [], [], "NONE")
    del step
    return videos, normal


def _write_annotation(
    path: Path,
    clip_id: str,
    fps: int,
    events: list[dict[str, Any]],
    occlusion: list[dict[str, Any]],
    hazard: str,
) -> None:
    path.write_text(
        json.dumps(
            {
                "clip_id": clip_id,
                "station_config_version": 1,
                "recorded_at": None,
                "fps": fps,
                "events": events,
                "occlusion_intervals": occlusion,
                "hazard_label": hazard,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


# ---- report --------------------------------------------------------------------------------------


def annotated_clips(directory: Path) -> list[tuple[Path, VideoAnnotation]]:
    out: list[tuple[Path, VideoAnnotation]] = []
    for video in sorted(directory.glob("*.mp4")):
        sidecar = video.with_suffix(".json")
        if sidecar.is_file():
            out.append((video, load_annotation(sidecar)))
    return out


def evaluate_sets(
    loaded: LoadedConfig, videos_dir: Path, normal_dir: Path
) -> tuple[list[ClipScore], list[str], list[dict[str, Any]], float]:
    cfg, station, k = to_domain(loaded)
    notes: list[str] = []
    scores: list[ClipScore] = []
    for video, annotation in annotated_clips(videos_dir):
        if str(annotation.station_config_version) != str(loaded.config_version):
            notes.append(
                f"{annotation.clip_id}: recorded under station_config_version "
                f"{annotation.station_config_version}, loaded {loaded.config_version} "
                "(20: recalibration invalidates fixtures)"
            )
        fps = annotation.fps or video_fps(video, loaded.values.capture.fps)
        emitted, frames = run_clip(loaded, station, video, fps)
        score = clip_score(annotation, emitted)
        scores.append(score)
        print(
            f"clip {annotation.clip_id}: {frames} frames, {len(emitted)} events, "
            f"{score.as_dict()['by_type']}"
        )

    normal_runs: list[dict[str, Any]] = []
    normal_seconds = 0.0
    if normal_dir.is_dir():
        for video in sorted(normal_dir.glob("*.mp4")):
            fps = video_fps(video, loaded.values.capture.fps)
            emitted, frames = run_clip(loaded, station, video, fps)
            duration_s = frames / fps
            normal_seconds += duration_s
            fold = fold_normal_clip(cfg, station, k, emitted)
            normal_runs.append(
                {
                    "clip": video.stem,
                    "frames": frames,
                    "duration_s": round(duration_s, 3),
                    "events": len(emitted),
                    "tier0_raises": fold.tier0,
                    "tier12_raises": fold.tier12,
                    "tier12_detail": fold.raises,
                }
            )
            print(
                f"normal {video.stem}: {duration_s:.1f} s, {len(emitted)} events, "
                f"tier1/2 raises {fold.tier12}"
            )
    return scores, notes, normal_runs, normal_seconds


def build_report(
    loaded: LoadedConfig,
    day: str,
    scores: list[ClipScore],
    notes: list[str],
    normal_runs: list[dict[str, Any]],
    normal_seconds: float,
    *,
    synthetic: bool,
    type_recall: float,
) -> dict[str, Any]:
    agg = aggregate(scores)
    tier12 = sum(int(r["tier12_raises"]) for r in normal_runs)
    nr = nuisance_rate(tier12, normal_seconds) if normal_seconds > 0 else None
    occlusion = agg["occlusion_recall"]
    recalls = {k: float(v["recall"]) for k, v in agg["by_type"].items()}
    failures: list[str] = []
    if not scores:
        failures.append("no annotated clips")
    if occlusion is None:
        failures.append(
            "no occlusion intervals annotated "
            "(35: they are the ground truth for the metric that matters most)"
        )
    elif occlusion < TARGET_OCCLUSION_RECALL:
        failures.append(f"occlusion recall {occlusion:.3f} < {TARGET_OCCLUSION_RECALL}")
    if nr is None:
        failures.append("no normal-prep footage (34: the normal-prep set is not optional)")
    elif nr >= TARGET_NUISANCE_PER_HOUR:
        failures.append(f"nuisance rate {nr:.2f}/h >= {TARGET_NUISANCE_PER_HOUR}")
    for kind, r in sorted(recalls.items()):
        if r < type_recall:
            failures.append(f"{kind} recall {r:.3f} < {type_recall}")
    return {
        "phase": "P4",
        "date": day,
        "synthetic": synthetic,
        "profile": loaded.profile,
        "station_id": loaded.station.station_id,
        "config_version": loaded.config_version,
        "config_checksum": loaded.config_checksum,
        "homography": "station file"
        if loaded.station.calibration.homography
        else "self-calibrated per clip from the corner markers",
        "clips": {s.clip_id: s.as_dict() for s in scores},
        "aggregate": agg,
        "occlusion_recall": occlusion,
        "nuisance_rate_per_hour": nr,
        "normal_minutes": round(normal_seconds / 60.0, 3),
        "normal_runs": normal_runs,
        "targets": {
            "occlusion_recall": TARGET_OCCLUSION_RECALL,
            "nuisance_rate_per_hour": TARGET_NUISANCE_PER_HOUR,
            "precision_recall": (
                "per 34 — targets not numerically fixed in docs; report the numbers"
            ),
            "per_type_recall_default": type_recall,
        },
        "passed": not failures,
        "failures": failures,
        "notes": [
            "Event matching: same type, |t_occurred - t_ms| <= 500 ms, participant set equal "
            "(CONTACT_* order-insensitive, GLOVE_CHANGE slot ignored); greedy one-to-one by "
            "smallest gap.",
            "Occlusion-reporting recall: an annotated interval counts when a "
            "CARRIER_OBSERVABILITY_CHANGED(UNKNOWN) for that carrier lands in "
            "[t_start - 1 s, t_end + 1 s].",
            "Emitted types the clip never annotates (heartbeat CARRIER_OBSERVABILITY_CHANGED "
            "TRACKED, HEALTH_DEGRADED, ...) are excluded from false-positive counting.",
            "CONTRACT-GAP: 34 gives no per-type precision/recall number; `passed` uses recall >= "
            f"{type_recall} per annotated type as this driver's default.",
            "Nuisance fold: normal prep carries no ticket, and Tier 1/2 needs a bound restricted "
            f"ticket, so the synthetic ticket {NUISANCE_TICKET[0]} ({NUISANCE_TICKET[1]}, "
            f"{NUISANCE_TICKET[2]!r}) is received, resolved, bound and started at t=0 of every "
            "normal clip. Tier 0 raises are counted separately and excluded from the rate by "
            "definition (34 §3).",
            "The pipeline is run offline: process_frame per decoded frame with "
            "t_ms = index * 1000 // fps; realtime=False; no threads, no persisted frames (24).",
            *(
                [
                    "Synthetic clips rendered by tests/perception/synth.py; this report is a "
                    "scorer self-test, not P4 evidence."
                ]
                if synthetic
                else []
            ),
            *notes,
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--videos", default=str(ROOT / "data" / "fixtures" / "video"))
    parser.add_argument("--normal", default=str(ROOT / "data" / "fixtures" / "normal"))
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument(
        "--out-dir", default=str(ROOT / "data" / "eval"), help="report root; <out-dir>/<date>/"
    )
    parser.add_argument("--profile", default="eval")
    parser.add_argument("--station", default="demo")
    parser.add_argument("--knowledge", default="demo")
    parser.add_argument("--type-recall", type=float, default=DEFAULT_TYPE_RECALL)
    parser.add_argument(
        "--synthetic", action="store_true", help="render and score synthetic clips instead"
    )
    args = parser.parse_args(argv)

    try:
        loaded = load(ROOT / "config", args.profile, args.station, args.knowledge, environ={})  # type: ignore[arg-type]
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2

    if args.synthetic:
        with tempfile.TemporaryDirectory(prefix="p4-synthetic-") as tmp:
            videos_dir, normal_dir = render_synthetic(Path(tmp), loaded.values.capture.fps)
            scores, notes, normal_runs, normal_seconds = evaluate_sets(
                loaded, videos_dir, normal_dir
            )
    else:
        videos_dir, normal_dir = Path(args.videos), Path(args.normal)
        if not annotated_clips(videos_dir) if videos_dir.is_dir() else True:
            print(
                f"no annotated clips in {videos_dir}. Record them at the station:\n"
                "  python scripts/record_fixture.py <clip_id> --seconds 60"
                "      # then fill <clip_id>.json\n"
                "  python scripts/record_fixture.py normal-01 --seconds 600 --normal\n"
                "(35 §Minimum viable dataset: 12 annotated clips + 30 min of normal prep)",
                file=sys.stderr,
            )
            return 1
        scores, notes, normal_runs, normal_seconds = evaluate_sets(loaded, videos_dir, normal_dir)

    report = build_report(
        loaded,
        args.date,
        scores,
        notes,
        normal_runs,
        normal_seconds,
        synthetic=args.synthetic,
        type_recall=args.type_recall,
    )
    out = Path(args.out_dir) / args.date / "p4_perception_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(
        f"occlusion recall {report['occlusion_recall']}, "
        f"nuisance {report['nuisance_rate_per_hour']}/h over {report['normal_minutes']} min, "
        f"per-type {report['aggregate']['by_type']}"
    )
    print("PASSED" if report["passed"] else "FAILED: " + "; ".join(report["failures"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
