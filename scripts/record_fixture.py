#!/usr/bin/env python
"""Record an evaluation fixture and its annotation skeleton (35, 34 §Benchmark sets).

    python scripts/record_fixture.py <clip_id> --seconds 60 [--source ...] [--normal] [--fps 15]
                                     [--force] [--no-preview]

Shows a 3-second countdown, then records `--seconds` of video to
`data/fixtures/video/<clip_id>.mp4` (or `data/fixtures/normal/` with `--normal`) with
cv2.VideoWriter (mp4v) at the camera's native size, printing elapsed seconds. Alongside it
writes `<clip_id>.json` — the 35 annotation skeleton for a person to fill — and
`<clip_id>.README.md` explaining how. Refuses to overwrite an existing clip without
`--force`.

Privacy (24): recordings are development/evaluation data only. `data/` is gitignored and
frames are written nowhere else. Do not record people who have not agreed to it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.runtime.config import ConfigError, load  # noqa: E402

README = """# {clip_id} — how to annotate

Fill `{clip_id}.json` by hand while scrubbing the video (35 §Annotation schema). Annotation
is at the **event** level: list the events perception is obliged to emit (21), not frames.

## `events`
One object per ground-truth event, in time order:

    {{"t_ms": 4120, "type": "ZONE_ENTRY", "participants": ["gloves"], "zone_id": "bin:pesto",
      "ground_truth": true}}

* `t_ms` — station time in milliseconds from the first frame (frame_index * 1000 / fps).
* `type` — one of ZONE_ENTRY, ZONE_EXIT, CONTACT_BEGIN, CONTACT_END, GLOVE_CHANGE,
  TOOL_SWAP, SURFACE_SWAP, SURFACE_WIPE, WASH_CYCLE, CARRIER_OBSERVABILITY_CHANGED,
  TRACK_IDENTITY_SUSPECT.
* `participants` — carrier ids from config/station/<station>.yaml (`gloves`, `spreader`,
  `board`, `landing`, `bin:pesto`, ...). ZONE_*: the carrier (put the zone in `zone_id`).
  CONTACT_*: both carriers, any order. TOOL_SWAP/SURFACE_SWAP: [retired, introduced].
  GLOVE_CHANGE: ["gloves"] (the slot is not scored).
* `zone_id` — only for zone events (optional elsewhere).
* `ground_truth` — always `true`.

The scorer matches an emitted event to an annotated one when type, participants and time
(within 500 ms) agree, so mark the moment the condition *becomes true* (the glove crosses
the bin edge), not when you noticed it.

## `occlusion_intervals`
Every interval in which a carrier was truly not visible to the camera — a hand under the
counter, a board under a tray, a body blocking the lens:

    {{"carrier_id": "gloves", "t_start": 12000, "t_end": 16500}}

This is tedious and it is the ground truth for the most important perception metric
(occlusion-reporting recall, 34). Annotate every one, even short ones.

## `hazard_label`
One of `NONE` | `DIRECT` | `TOOL` | `SURFACE` | `BACK_CONTAMINATION` — the contamination
pathway class the clip demonstrates (14 §Pathway classes). Normal prep is `NONE`.

## Do not edit
`station_config_version` is the calibration this clip was recorded under; a recalibration
(scripts/calibrate.py --write) bumps it and invalidates the clip (20 §Station frame).
"""


def resolve_source(raw: str | None, fallback: int | str) -> int | str:
    if raw is None:
        raw = os.environ.get("STATION_CAMERA")
    if raw is None:
        return fallback
    return int(raw) if raw.isdigit() else raw


def skeleton(clip_id: str, config_version: int, fps: int, recorded_at: str) -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "station_config_version": config_version,
        "recorded_at": recorded_at,
        "fps": fps,
        "events": [],
        "occlusion_intervals": [],
        "hazard_label": "NONE",
    }


def write_sidecars(
    directory: Path, clip_id: str, config_version: int, fps: int, recorded_at: str
) -> None:
    (directory / f"{clip_id}.json").write_text(
        json.dumps(skeleton(clip_id, config_version, fps, recorded_at), indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / f"{clip_id}.README.md").write_text(
        README.format(clip_id=clip_id), encoding="utf-8"
    )


def _overlay(frame: object, text: str) -> None:
    cv2.putText(frame, text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(
        frame, text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 2, cv2.LINE_AA
    )


def record(
    source: int | str, out: Path, seconds: float, fps: int, preview: bool
) -> tuple[int, int, int]:
    """Countdown, then record; returns (frames written, width, height)."""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"cannot open camera/video source {source!r}")
    window = "record_fixture"
    writer = None
    written = 0
    width = height = 0
    try:
        ok, frame = cap.read()
        if not ok:
            raise SystemExit("camera delivered no frame")
        height, width = frame.shape[:2]
        if preview:
            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 3.0:  # countdown: the person gets into position
            ok, frame = cap.read()
            if not ok:
                raise SystemExit("camera stopped during countdown")
            remaining = 3 - int(time.monotonic() - t0)
            if preview:
                _overlay(frame, f"recording in {remaining}")
                cv2.imshow(window, frame)
                cv2.waitKey(1)
        writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        if not writer.isOpened():
            raise SystemExit(f"cannot open VideoWriter for {out}")
        print("recording")
        start = time.monotonic()
        last_printed = -1
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= seconds:
                break
            ok, frame = cap.read()
            if not ok:
                print("camera stopped early", file=sys.stderr)
                break
            writer.write(frame)
            written += 1
            if int(elapsed) != last_printed:
                last_printed = int(elapsed)
                print(f"  {last_printed:3d} s / {seconds:g} s", flush=True)
            if preview:
                view = frame.copy()
                _overlay(view, f"REC {elapsed:5.1f} s")
                cv2.imshow(window, view)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    print("stopped by key")
                    break
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if preview:
            cv2.destroyAllWindows()
    return written, width, height


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("clip_id", help="file stem, e.g. 03-tool-transfer or normal-01")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument(
        "--source", default=None, help="camera index or video path; STATION_CAMERA env"
    )
    parser.add_argument("--normal", action="store_true", help="record into data/fixtures/normal/")
    parser.add_argument("--fps", type=int, default=None, help="writer fps (default: capture.fps)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing clip")
    parser.add_argument("--no-preview", action="store_true", help="no window (headless capture)")
    parser.add_argument("--station", default="demo")
    parser.add_argument("--fixtures-root", default=str(ROOT / "data" / "fixtures"))
    args = parser.parse_args(argv)

    if "/" in args.clip_id or args.clip_id.startswith("."):
        print("clip_id must be a bare file stem", file=sys.stderr)
        return 2
    try:
        loaded = load(ROOT / "config", "dev", args.station, "demo", environ={})
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    fps = args.fps or loaded.values.capture.fps
    directory = Path(args.fixtures_root) / ("normal" if args.normal else "video")
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / f"{args.clip_id}.mp4"
    if out.exists() and not args.force:
        print(
            f"{out} exists; pass --force to overwrite (its annotation would be lost)",
            file=sys.stderr,
        )
        return 1

    source = resolve_source(args.source, loaded.values.perception.camera.source)
    recorded_at = datetime.now().astimezone().isoformat(timespec="seconds")
    written, width, height = record(source, out, args.seconds, fps, preview=not args.no_preview)
    write_sidecars(directory, args.clip_id, loaded.config_version, fps, recorded_at)
    print(f"wrote {out}: {written} frames, {width}x{height} @ {fps} fps")
    print(f"wrote {directory / (args.clip_id + '.json')} (annotation skeleton) and README")
    if not args.normal:
        print(
            "next: fill events / occlusion_intervals / hazard_label, "
            "then scripts/eval_perception.py"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
