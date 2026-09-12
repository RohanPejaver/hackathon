#!/usr/bin/env python
"""Establish the station frame from the four corner markers (20 §Station frame, 39 §3).

    python scripts/calibrate.py [--source STATION_CAMERA|0|file] [--frames 30] [--station demo]
                                [--frame-file x.png] [--dry-run | --write] [--max-error-mm 3]

Grabs `--frames` frames (or the single `--frame-file`), detects the corner markers in each,
takes the per-id median centre over the frames where all four are present, fits the
pixel -> mm homography and prints it with its reprojection error. `--dry-run` (the default)
writes nothing. `--write` stores `calibration.homography` in config/station/<station>.yaml
and bumps `config_version` by one — a calibration change invalidates every recorded fixture
(20). Writing is refused when the reprojection error exceeds `--max-error-mm`.

YAML caveat: ruamel is not a dependency, so the station file is round-tripped with PyYAML
(`sort_keys=False`); key order survives but **comments in config/station/<station>.yaml are
lost**. Re-add them from git if they matter, or write the homography by hand from the
printed matrix.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.perception.calibration import (  # noqa: E402
    detect_corners,
    homography_from_corners,
    reprojection_error_mm,
)
from src.runtime.config import ConfigError, load  # noqa: E402


def resolve_source(raw: str | None) -> int | str:
    """`STATION_CAMERA` (env) > explicit value > config `perception.camera.source`."""
    if raw is None:
        raw = os.environ.get("STATION_CAMERA")
    if raw is None:
        return 0
    return int(raw) if raw.isdigit() else raw


def grab_frames(source: int | str, count: int) -> list[np.ndarray]:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"cannot open camera/video source {source!r}")
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


def median_corners(
    frames: list[np.ndarray], dictionary: str, corner_ids: tuple[int, int, int, int]
) -> tuple[dict[int, tuple[float, float]], int]:
    """Per-id median centre over the frames where all four corners were detected."""
    seen: dict[int, list[tuple[float, float]]] = {i: [] for i in corner_ids}
    usable = 0
    for frame in frames:
        found = detect_corners(frame, dictionary, corner_ids)
        if any(i not in found for i in corner_ids):
            continue
        usable += 1
        for i in corner_ids:
            seen[i].append((float(found[i][0]), float(found[i][1])))
    if usable == 0:
        return {}, 0
    return {
        i: (statistics.median(x for x, _ in pts), statistics.median(y for _, y in pts))
        for i, pts in seen.items()
    }, usable


def bump_station_file(path: Path, homography: list[list[float]]) -> int:
    """Write the homography and bump config_version; returns the new version."""
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["calibration"]["homography"] = homography
    data["config_version"] = int(data["config_version"]) + 1
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return int(data["config_version"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source", default=None, help="camera index or video path; STATION_CAMERA env"
    )
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--frame-file", default=None, help="calibrate from a single image instead")
    parser.add_argument("--station", default="demo")
    parser.add_argument("--config-root", default=str(ROOT / "config"), help="config directory")
    parser.add_argument("--max-error-mm", type=float, default=3.0)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write", action="store_true", help="store the homography, bump config_version"
    )
    mode.add_argument("--dry-run", action="store_true", help="print only (default)")
    args = parser.parse_args(argv)

    config_root = Path(args.config_root)
    try:
        loaded = load(config_root, "dev", args.station, "demo", environ={})
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    markers = loaded.values.perception.markers
    corner_ids = (
        markers.corner_ids[0],
        markers.corner_ids[1],
        markers.corner_ids[2],
        markers.corner_ids[3],
    )
    cal = loaded.station.calibration

    if args.frame_file:
        frame = cv2.imread(args.frame_file)
        if frame is None:
            print(f"cannot read {args.frame_file}", file=sys.stderr)
            return 2
        frames = [frame]
    else:
        source = resolve_source(args.source)
        if args.source is None and "STATION_CAMERA" not in os.environ:
            source = loaded.values.perception.camera.source
        frames = grab_frames(source, args.frames)

    corners, usable = median_corners(frames, markers.dictionary, corner_ids)
    print(f"frames: {len(frames)}, with all four corners: {usable}")
    if usable == 0:
        print(
            "no frame showed all four corner markers; check lighting, focus and ids",
            file=sys.stderr,
        )
        return 1
    for i in corner_ids:
        print(f"  id {i}: centre px = ({corners[i][0]:.1f}, {corners[i][1]:.1f})")

    H = np.asarray(
        homography_from_corners(corners, corner_ids, cal.width_mm, cal.height_mm), dtype=float
    )
    error = float(reprojection_error_mm(H, corners, corner_ids, cal.width_mm, cal.height_mm))
    print("homography (px -> mm):")
    for row in H:
        print("  [" + ", ".join(f"{v: .6f}" for v in row) + "]")
    print(f"reprojection error: {error:.3f} mm (limit {args.max_error_mm:g} mm)")
    if error > args.max_error_mm:
        print(
            "error above limit: refusing to write. Re-tape the markers flat and retry.",
            file=sys.stderr,
        )
        return 1
    if not args.write:
        print("dry run: nothing written (use --write to store it and bump config_version)")
        return 0

    station_path = config_root / "station" / f"{args.station}.yaml"
    new_version = bump_station_file(station_path, [[float(v) for v in row] for row in H])
    reloaded = load(config_root, "dev", args.station, "demo", environ={})
    print(f"wrote {station_path}: config_version {loaded.config_version} -> {new_version}")
    print(f"config checksum: {reloaded.config_checksum}")
    print("note: PyYAML round-trip dropped the comments in that file (see --help).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
