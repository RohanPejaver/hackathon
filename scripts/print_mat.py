"""Print the "station on a mat": two sheets that tape together into the mat described by a
station file (corner ArUco markers at the frame corners, zone outlines and labels drawn on).

    python scripts/print_mat.py [--station mat] [--paper letter|a4] [--dpi 300] [--out data/markers]

Sheets: two portrait pages side by side; the station frame (between marker centres) is
`calibration.width_mm x height_mm`. Print at 100% scale, tape the inner edges together.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from src.runtime.config import load

PAPER = {"letter": (215.9, 279.4), "a4": (210.0, 297.0)}  # portrait, mm


def mm_px(mm: float, dpi: int) -> int:
    return int(round(mm / 25.4 * dpi))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--station", default="mat")
    ap.add_argument("--paper", default="letter", choices=list(PAPER))
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default="data/markers")
    ap.add_argument("--corner-mm", type=float, default=30.0)
    args = ap.parse_args()
    loaded = load("config", "dev", args.station, "demo", environ={})
    st = loaded.station
    p = loaded.values.perception
    frame_w, frame_h = st.calibration.width_mm, st.calibration.height_mm
    pw, ph = PAPER[args.paper]
    mat_w, mat_h = 2 * pw, ph
    if frame_w + 2 * args.corner_mm > mat_w or frame_h + 2 * args.corner_mm > mat_h:
        raise SystemExit(f"frame {frame_w}x{frame_h} mm does not fit two {args.paper} sheets")
    ox, oy = (mat_w - frame_w) / 2, (mat_h - frame_h) / 2  # frame origin on the mat (mm)
    dpi = args.dpi
    W, H = mm_px(mat_w, dpi), mm_px(mat_h, dpi)
    img = np.full((H, W, 3), 255, np.uint8)

    def pt(x_mm: float, y_mm: float) -> tuple[int, int]:
        # station y grows toward the back; image y grows downward, so the front edge is at
        # the bottom of the sheet (the presenter stands at the front).
        return mm_px(ox + x_mm, dpi), mm_px(oy + (frame_h - y_mm), dpi)

    # zones
    for z in st.zones:
        pts = np.array([pt(x, y) for x, y in z.polygon], np.int32)
        cv2.polylines(img, [pts], True, (60, 60, 60), max(2, dpi // 150))
        cx, cy = pts.mean(axis=0).astype(int)
        label = (z.contents[0] if z.contents else z.zone_id).upper()
        cv2.putText(
            img,
            label,
            (cx - 18 * len(label) // 2, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            dpi / 300 * 1.1,
            (90, 90, 90),
            max(2, dpi // 150),
            cv2.LINE_AA,
        )
    # corner markers, centred on the frame corners
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, p.markers.dictionary))
    size = mm_px(args.corner_mm, dpi)  # smaller than the table markers so the sheet stays usable
    corners = {0: (0, 0), 1: (frame_w, 0), 2: (frame_w, frame_h), 3: (0, frame_h)}
    for mid, (x, y) in zip(p.markers.corner_ids, [corners[i] for i in range(4)], strict=True):
        m = cv2.aruco.generateImageMarker(dic, mid, size)
        cx, cy = pt(x, y)
        quiet = size // 6
        x0, y0 = cx - size // 2, cy - size // 2
        img[y0 - quiet : y0 + size + quiet, x0 - quiet : x0 + size + quiet] = 255
        img[y0 : y0 + size, x0 : x0 + size] = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)
        cv2.putText(
            img,
            f"id {mid}",
            (x0, y0 + size + quiet + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )
    cv2.putText(
        img,
        f"STATION MAT {frame_w:.0f}x{frame_h:.0f} mm  -  print 100% scale, tape the centre seam",
        (mm_px(10, dpi), mm_px(8, dpi)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    half = W // 2
    cv2.imwrite(str(out / f"mat_{args.paper}_A.png"), img[:, :half])
    cv2.imwrite(str(out / f"mat_{args.paper}_B.png"), img[:, half:])
    cv2.imwrite(str(out / f"mat_{args.paper}_preview.png"), cv2.resize(img, (W // 4, H // 4)))
    print(f"wrote {out}/mat_{args.paper}_A.png + _B.png ({pw:.0f}x{ph:.0f} mm each), _preview.png")
    print(
        f"corner markers {args.corner_mm:.0f} mm at the {frame_w:.0f}x{frame_h:.0f} mm frame corners"
    )


if __name__ == "__main__":
    main()
