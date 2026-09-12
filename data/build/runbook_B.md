# Run Book — the two-minute demo and the fallback ladder (Device B draft)

Source: `docs/engineering/37-demo-plan.md` §Script, §Determinism under pressure. A verifies
each beat runs at convergence. **No camera exists in this build: every run below is
`PROTOCOL_ONLY` or `REPLAY`.** Ladder level 1 (live perception) is recorded as N/A.

## Start

```bash
source .venv/bin/activate
uvicorn src.runtime.app:app --host 127.0.0.1 --port 8000        # profile=demo, PROTOCOL_ONLY, no camera
# or the scripted beats:  STATION_REPLAY=scenarios/demo.yaml uvicorn src.runtime.app:app
```

Open `http://127.0.0.1:8000/` on the station display (dark, full-screen). Open
`/inspector` on the presenter's laptop, second window. Confirm the mode banner reads
**PROTOCOL ONLY — vision unavailable** and the carrier grid shows all carriers `UNKNOWN`.

## Script — beat by beat (spoken line · action · what the screen must show)

| Beat | Say | Do | Screen must show |
|---|---|---|---|
| **0 · Setup** (15s) | "Four things carry allergens at this station: gloves, spreader, board, landing. Plus the shared bins." | Nothing | Carrier grid: 8 tiles, quiet. No alert. Worker surface empty. |
| **1 · Ticket 47** (25s) | "Ticket 47, pesto sandwich, no restriction. Watch how little happens." | Tap **NEW TICKET → 47 pesto_sandwich, no restriction → BIND**. Scoop pesto, spread, plate (in `PROTOCOL_ONLY`: assert the contacts from the inspector timeline / fixture feed) | **Silence.** `gloves`, `spreader`, `board` tiles turn **amber** with `PINE_NUT`. No alert of any tier. |
| **2 · The reach** (10s) | "Now — same gloves — into the mayo tub." | Contact `gloves ↔ bin:mayo` | `bin:mayo` tile flips amber: **"Shared container — PINE_NUT — affects all future tickets"** |
| **3 · Ticket 48** (30s) | "Ticket 48. Turkey sandwich. Pine-nut allergy." | Tap **NEW TICKET → 48 turkey_sandwich, restriction "pine nut allergy" → BIND** | **Tier 0 before any motion**: `PINE NUT — station not clean` · ☐ New gloves · ☐ Clean spreader · **! Mayo container flagged — use sealed backup** |
| **4 · Compliance** (20s) | "Change gloves, swap the spreader." | `GLOVE_CHANGE(DON)`, `TOOL_SWAP(spreader → spreader_2)` (in `PROTOCOL_ONLY`: tap **Already swapped** / **Already clean** — `ASSERTED` grade) | Checklist items **tick themselves off**; carriers return to quiet; prompt clears; silence resumes. |
| **5 · Failure branch** (20s) | "Rerun 48 and ignore the prompt." | Bind 48 again on the dirty state; build with the dirty spreader; mark **ITEM COMPLETE** | **HOLD — TICKET 48 — DO NOT SEND** · full evidence trace incl. the absence line · *"This is an observation, not a determination. Confirm with the cook."* · `[Cook confirms tool was clean]` `[Remake]` |
| **6 · Close** (10s) | "It doesn't replace the protocol. It checks that the protocol happened." | — | — |

## Fallback ladder — all three levels must produce identical UI

| Level | Source | How to start | Status |
|---|---|---|---|
| 1 | Live perception | camera + `.[perception]` | **N/A — no camera in this build** |
| 2 | Recorded log replay | `STATION_REPLAY=data/logs/<session>.jsonl uvicorn src.runtime.app:app` (any JSONL written by a prior session) | **rehearsed 12:40 — identical to level 3** (`data/eval/2026-09-12/p3_fallback_ladder.json`) |
| 3 | Scenario replay | `STATION_REPLAY=scenarios/demo.yaml uvicorn src.runtime.app:app` | **rehearsed 12:38 — every beat on the display** |

Drill: start level 3, then level 2, screenshot both at beats 2, 3, 5; diff the snapshots
byte-for-byte via `/inspector` export. Record the result in `status_B.md`.

## Camera-unplug drill (rehearse once for real)

With no camera there is no FULL mode to fall from, so the drill is scenario L replayed through
the display: `STATION_REPLAY=scenarios/L-camera-fault-mid-ticket.yaml uvicorn src.runtime.app:app`.
Watch: Tier 2 hold raised → `STATION_MODE_CHANGED(PROTOCOL_ONLY, camera fault)` → every carrier
`UNKNOWN`, banner **PROTOCOL ONLY — VISION UNAVAILABLE** → the hold persists → the next
restricted bind still gets Tier 0. Narrate it: *"A failure that is part of the script is not a
failure."*

## Tap-count measurement (P3 gate — measured on a teammate, not the author)

| Tier | Alert | Resolving action | Taps (teammate) | Who | When |
|---|---|---|---|---|---|
| 0 | Reset prompt | Already clean / Already swapped per item | | | |
| 1 | Interrupt | Already swapped | | | |
| 2 | Hold | Cook confirms tool was clean **or** Remake | | | |

## Field procedure — bringing perception up (P4/P5)

Prerequisites: a table (1200 × 600 mm work area), an overhead camera fixed straight down at
1.0–1.3 m, blue/purple nitrile gloves, a white mat or cloth, matte-printed markers.

```bash
source .venv/bin/activate && pip install -e '.[dev,perception]'
python scripts/print_markers.py                       # PNGs -> data/markers/ (+ SHEET.md placement guide)
#   tape corners: id 0 front-left (origin), 1 front-right, 2 back-right, 3 back-left; tools ids 10-12; boards 20-21
export STATION_CAMERA=0                               # device index, or a video file path
python scripts/calibrate.py --source 0 --frames 30    # dry run: prints the homography + reprojection error (mm)
python scripts/calibrate.py --source 0 --write        # writes calibration.homography, bumps config_version
python scripts/tune_hsv.py --source 0                 # trackbars; aim for one solid blob on each glove, none elsewhere
python scripts/tune_hsv.py --source 0 --write         # stores the thresholds in config/defaults.yaml
python scripts/record_fixture.py clean_prep --seconds 60         # one clip per 35 §Minimum viable dataset (12 total)
python scripts/record_fixture.py normal_01 --seconds 600 --normal  # 30 minutes total of hazard-free prep
#   then fill data/fixtures/video/<clip>.json events + occlusion_intervals from the video
python scripts/eval_perception.py                      # -> data/eval/<date>/p4_perception_report.json (the P4 gate)
STATION_CAMERA=0 uvicorn src.runtime.app:app           # live: FULL once the camera reports healthy frames
```

Order matters: markers before calibration, calibration before HSV tuning (the mat changes the
white balance), tuning before recording, recording before eval. Re-run `calibrate.py --write`
after ANY camera move — it bumps `config_version`, which is what invalidates old fixtures (20).

Clips to record (30–90 s each; annotate at the event level, including occlusion intervals):
`clean_prep`, `direct_transfer`, `tool_transfer`, `surface_transfer`, `back_contamination`,
`glove_change`, `tool_swap`, `wipe`, `occlusion`, `identity_confusion`, `two_tickets`,
`camera_obstruction`; plus `normal_01..normal_03` (10 min each, `--normal`).
