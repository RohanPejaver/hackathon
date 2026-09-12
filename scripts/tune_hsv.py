#!/usr/bin/env python
"""Tune the glove HSV thresholds at the venue, not at home (39 §11).

    python scripts/tune_hsv.py [--source STATION_CAMERA|0|file]                  # interactive
    python scripts/tune_hsv.py --headless [--frames N | --frame-file x.png] [--write]

Interactive mode opens an OpenCV window with six trackbars (H/S/V lower and upper) seeded
from `perception.gloves` and shows the mask, the largest blob's outline and its area; press
`w` to write the current values, `q`/Esc to quit. `--headless` processes N frames (or one
image) and prints, for the configured thresholds and for +-10 hue / +-20 saturation
variants, the largest blob's area and confidence so a person can pick a range without a
display. `--write` stores `perception.gloves.hsv_lower/hsv_upper` in config/defaults.yaml.

YAML caveat: PyYAML round-trip (`sort_keys=False`) keeps key order but **drops the comments
in config/defaults.yaml**. Restore them from git afterwards if they matter.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.perception.segment import glove_blob  # noqa: E402
from src.runtime.config import ConfigError, load  # noqa: E402

HSV = tuple[int, int, int]
_VARIANTS: list[tuple[str, int, int]] = [  # (label, hue delta, saturation delta)
    ("configured", 0, 0),
    ("hue -10", -10, 0),
    ("hue +10", 10, 0),
    ("sat -20", 0, -20),
    ("sat +20", 0, 20),
]


def resolve_source(raw: str | None, fallback: int | str) -> int | str:
    if raw is None:
        raw = os.environ.get("STATION_CAMERA")
    if raw is None:
        return fallback
    return int(raw) if raw.isdigit() else raw


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def variant(lower: HSV, upper: HSV, dh: int, ds: int) -> tuple[HSV, HSV]:
    lo = (_clamp(lower[0] + dh, 0, 179), _clamp(lower[1] + ds, 0, 255), lower[2])
    hi = (_clamp(upper[0] + dh, 0, 179), _clamp(upper[1] + ds, 0, 255), upper[2])
    return lo, hi


def read_frames(source: int | str, count: int) -> list[np.ndarray]:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {source!r}")
    frames: list[np.ndarray] = []
    try:
        while len(frames) < count:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
    finally:
        cap.release()
    if not frames:
        raise SystemExit(f"no frames from {source!r}")
    return frames


def headless_report(
    frames: list[np.ndarray], lower: HSV, upper: HSV, min_area_px: int
) -> list[dict[str, Any]]:
    """Per variant: how many frames had a blob, mean area and mean confidence."""
    rows: list[dict[str, Any]] = []
    for label, dh, ds in _VARIANTS:
        lo, hi = variant(lower, upper, dh, ds)
        areas: list[float] = []
        confidences: list[float] = []
        for frame in frames:
            blob = glove_blob(frame, lo, hi, min_area_px)
            if blob is not None:
                areas.append(float(blob.area_px))
                confidences.append(float(blob.confidence))
        rows.append(
            {
                "variant": label,
                "hsv_lower": list(lo),
                "hsv_upper": list(hi),
                "frames_with_blob": len(areas),
                "frames": len(frames),
                "mean_area_px": (sum(areas) / len(areas)) if areas else 0.0,
                "mean_confidence": (sum(confidences) / len(confidences)) if confidences else 0.0,
            }
        )
    return rows


def write_defaults(path: Path, lower: HSV, upper: HSV) -> None:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    gloves = data["perception"]["gloves"]
    gloves["hsv_lower"] = [int(v) for v in lower]
    gloves["hsv_upper"] = [int(v) for v in upper]
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def interactive(
    source: int | str, lower: HSV, upper: HSV, min_area_px: int
) -> tuple[HSV, HSV, bool]:
    window = "tune_hsv  (w = write, q = quit)"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    names = ("H lo", "S lo", "V lo", "H hi", "S hi", "V hi")
    seeds = (*lower, *upper)
    limits = (179, 255, 255, 179, 255, 255)
    for name, seed, limit in zip(names, seeds, limits, strict=True):
        cv2.createTrackbar(name, window, int(seed), limit, lambda _v: None)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"cannot open source {source!r}")
    want_write = False
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop a file; a dead camera just spins
                continue
            values = [cv2.getTrackbarPos(n, window) for n in names]
            lower = (values[0], values[1], values[2])
            upper = (values[3], values[4], values[5])
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(
                hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8)
            )
            view = cv2.addWeighted(frame, 0.5, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), 0.5, 0)
            blob = glove_blob(frame, lower, upper, min_area_px)
            text = "no blob >= min_area"
            if blob is not None:
                x, y, w, h = (int(v) for v in blob.bbox)
                cv2.rectangle(view, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cx, cy = (int(v) for v in blob.centroid_px)
                cv2.circle(view, (cx, cy), 6, (0, 0, 255), -1)
                text = f"area {int(blob.area_px)} px  conf {blob.confidence:.2f}"
            cv2.putText(
                view,
                f"{text}  lo={lower} hi={upper}",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.imshow(window, view)
            key = cv2.waitKey(30) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("w"):
                want_write = True
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return lower, upper, want_write


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source", default=None, help="camera index or video path; STATION_CAMERA env"
    )
    parser.add_argument("--headless", action="store_true", help="no window; print a variant table")
    parser.add_argument("--frames", type=int, default=30, help="frames to sample in headless mode")
    parser.add_argument("--frame-file", default=None, help="single image instead of a stream")
    parser.add_argument(
        "--write", action="store_true", help="store the chosen thresholds in defaults.yaml"
    )
    parser.add_argument("--config-root", default=str(ROOT / "config"))
    parser.add_argument("--lower", default=None, help="override, e.g. 95,80,60 (headless --write)")
    parser.add_argument(
        "--upper", default=None, help="override, e.g. 140,255,255 (headless --write)"
    )
    args = parser.parse_args(argv)

    config_root = Path(args.config_root)
    try:
        loaded = load(config_root, "dev", "demo", "demo", environ={})
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    gloves = loaded.values.perception.gloves
    lower: HSV = (int(gloves.hsv_lower[0]), int(gloves.hsv_lower[1]), int(gloves.hsv_lower[2]))
    upper: HSV = (int(gloves.hsv_upper[0]), int(gloves.hsv_upper[1]), int(gloves.hsv_upper[2]))
    if args.lower:
        h, s, v = (int(x) for x in args.lower.split(","))
        lower = (h, s, v)
    if args.upper:
        h, s, v = (int(x) for x in args.upper.split(","))
        upper = (h, s, v)

    if args.frame_file:
        frame = cv2.imread(args.frame_file)
        if frame is None:
            print(f"cannot read {args.frame_file}", file=sys.stderr)
            return 2
        frames = [frame]
        source: int | str = args.frame_file
    else:
        source = resolve_source(args.source, loaded.values.perception.camera.source)
        frames = read_frames(source, args.frames) if args.headless else []

    if args.headless:
        rows = headless_report(frames, lower, upper, gloves.min_area_px)
        print(
            f"{'variant':<12}{'lower':<18}{'upper':<18}{'blob frames':>12}"
            f"{'mean area px':>14}{'mean conf':>11}"
        )
        for r in rows:
            print(
                f"{r['variant']:<12}{str(r['hsv_lower']):<18}{str(r['hsv_upper']):<18}"
                f"{r['frames_with_blob']:>5}/{r['frames']:<6}{r['mean_area_px']:>14.0f}"
                f"{r['mean_confidence']:>11.2f}"
            )
        print(
            f"blob area (configured): {rows[0]['mean_area_px']:.0f} px "
            f"over {rows[0]['frames_with_blob']} frame(s)"
        )
        want_write = args.write
    else:
        lower, upper, pressed = interactive(source, lower, upper, gloves.min_area_px)
        want_write = args.write or pressed

    if want_write:
        path = config_root / "defaults.yaml"
        write_defaults(path, lower, upper)
        print(f"wrote perception.gloves.hsv_lower={list(lower)} hsv_upper={list(upper)} to {path}")
        print("note: PyYAML round-trip dropped the comments in that file (see --help).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
