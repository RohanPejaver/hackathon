# Marker sheet

Dictionary `DICT_4X4_50`, rendered at 300 dpi. **Print at 100% scale** (no
'fit to page'), on **matte** paper — gloss reflects the overhead light and blinds the
detector. Check one corner marker with a ruler after printing: the black square must
measure the size in the caption.

## Station frame corners (20 §Station frame)

Tape flat at the four corners of the 1200 x 600 mm work surface, in this order when
seen from the worker's side. The marker's centre is the calibration point, so keep
the centres on the table's corners, not the paper's edges.

| id | position |
|---|---|
| 0 | front-left — the station-frame **origin** (0, 0) |
| 1 | front-right — (width, 0) |
| 2 | back-right — (width, height) |
| 3 | back-left — (0, height) |

Do not move them after `scripts/calibrate.py --write`; moving one invalidates every
recorded fixture and bumps `config_version`.

## Tools and surfaces (39 §3)

Tool markers go on the **handle**, facing the camera when the tool lies in its rack.
Surface markers go on a corner of the board that the hands do not cover.

| id | file | role | size (mm) |
|---|---|---|---|
| 0 | `corner_00.png` | corner front-left (origin) | 80 |
| 1 | `corner_01.png` | corner front-right | 80 |
| 2 | `corner_02.png` | corner back-right | 80 |
| 3 | `corner_03.png` | corner back-left | 80 |
| 10 | `tool_10_spreader.png` | tool spreader | 25 |
| 11 | `tool_11_spreader_2.png` | tool spreader_2 | 25 |
| 12 | `tool_12_spreader_3.png` | tool spreader_3 | 25 |
| 20 | `surface_20_board.png` | surface board | 40 |
| 21 | `surface_21_board_2.png` | surface board_2 | 40 |
