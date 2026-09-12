#!/usr/bin/env python
"""Print-ready ArUco markers for the station (39 §3).

    python scripts/print_markers.py [--out data/markers] [--dpi 300] [--station demo]

Reads the config the runtime reads (defaults + profile + station) and renders one PNG per
marker at physical size for the requested dpi: the four station-frame corners at
`perception.markers.corner_size_mm`, every tool marker at `tool_size_mm`, every surface
marker at 40 mm. Each PNG carries a white quiet zone of one marker module on every side and
a caption (id, carrier, size) beneath. Also writes `SHEET.md` with placement instructions.
Idempotent: running twice produces identical files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.runtime.config import ConfigError, load  # noqa: E402

SURFACE_SIZE_MM = 40
CORNER_ROLES = ("front-left (origin)", "front-right", "back-right", "back-left")


def _dictionary(name: str) -> cv2.aruco.Dictionary:
    try:
        return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))
    except AttributeError as e:
        raise SystemExit(f"unknown ArUco dictionary {name!r}") from e


def render_marker(
    dictionary: cv2.aruco.Dictionary, marker_id: int, size_mm: float, dpi: int, caption: str
) -> np.ndarray:
    """Marker at physical size with a one-module quiet zone and a caption strip."""
    modules = int(dictionary.markerSize) + 2  # the marker's own black border counts as modules
    side_px = max(modules, int(round(size_mm / 25.4 * dpi)))
    quiet = max(1, side_px // modules)
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, side_px)
    strip = max(24, side_px // 6)
    canvas = np.full((side_px + 2 * quiet + strip, side_px + 2 * quiet), 255, dtype=np.uint8)
    canvas[quiet : quiet + side_px, quiet : quiet + side_px] = marker
    scale = max(0.4, side_px / 600.0)
    thickness = max(1, int(round(scale * 2)))
    cv2.putText(
        canvas,
        caption,
        (quiet, side_px + 2 * quiet + int(strip * 0.7)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        0,
        thickness,
        cv2.LINE_AA,
    )
    return canvas


def marker_plan(station: str) -> tuple[str, list[tuple[int, str, str, float]]]:
    """(dictionary name, [(id, role, filename stem, size_mm)]) from the loaded config."""
    loaded = load(ROOT / "config", "dev", station, "demo", environ={})
    markers = loaded.values.perception.markers
    plan: list[tuple[int, str, str, float]] = []
    for mid, role in zip(markers.corner_ids, CORNER_ROLES, strict=True):
        plan.append((mid, f"corner {role}", f"corner_{mid:02d}", float(markers.corner_size_mm)))
    for mid, carrier in sorted(loaded.station.markers.tools.items()):
        plan.append(
            (mid, f"tool {carrier}", f"tool_{mid:02d}_{carrier}", float(markers.tool_size_mm))
        )
    for mid, carrier in sorted(loaded.station.markers.surfaces.items()):
        plan.append(
            (mid, f"surface {carrier}", f"surface_{mid:02d}_{carrier}", float(SURFACE_SIZE_MM))
        )
    return markers.dictionary, plan


def write_sheet(
    out: Path, dictionary: str, plan: list[tuple[int, str, str, float]], dpi: int
) -> None:
    lines = [
        "# Marker sheet",
        "",
        f"Dictionary `{dictionary}`, rendered at {dpi} dpi. **Print at 100% scale** (no",
        "'fit to page'), on **matte** paper — gloss reflects the overhead light and blinds the",
        "detector. Check one corner marker with a ruler after printing: the black square must",
        "measure the size in the caption.",
        "",
        "## Station frame corners (20 §Station frame)",
        "",
        "Tape flat at the four corners of the 1200 x 600 mm work surface, in this order when",
        "seen from the worker's side. The marker's centre is the calibration point, so keep",
        "the centres on the table's corners, not the paper's edges.",
        "",
        "| id | position |",
        "|---|---|",
        "| 0 | front-left — the station-frame **origin** (0, 0) |",
        "| 1 | front-right — (width, 0) |",
        "| 2 | back-right — (width, height) |",
        "| 3 | back-left — (0, height) |",
        "",
        "Do not move them after `scripts/calibrate.py --write`; moving one invalidates every",
        "recorded fixture and bumps `config_version`.",
        "",
        "## Tools and surfaces (39 §3)",
        "",
        "Tool markers go on the **handle**, facing the camera when the tool lies in its rack.",
        "Surface markers go on a corner of the board that the hands do not cover.",
        "",
        "| id | file | role | size (mm) |",
        "|---|---|---|---|",
    ]
    for mid, role, stem, size in plan:
        lines.append(f"| {mid} | `{stem}.png` | {role} | {size:g} |")
    lines.append("")
    out.joinpath("SHEET.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", default="data/markers", help="output directory (gitignored)")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--station", default="demo", help="station config id")
    args = parser.parse_args(argv)

    try:
        dictionary_name, plan = marker_plan(args.station)
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    dictionary = _dictionary(dictionary_name)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for mid, role, stem, size in plan:
        image = render_marker(dictionary, mid, size, args.dpi, f"id {mid}  {role}  {size:g} mm")
        cv2.imwrite(str(out / f"{stem}.png"), image)
        print(f"wrote {out / f'{stem}.png'}  ({size:g} mm, id {mid}, {role})")
    write_sheet(out, dictionary_name, plan, args.dpi)
    print(f"wrote {out / 'SHEET.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
