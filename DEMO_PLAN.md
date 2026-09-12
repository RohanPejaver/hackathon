# DEMO PLAN — judged at 4:00 pm, 2026-09-12

Decision: **option 3 + option 2**. The main show is the real product driven by the replay
fixture on the projector (deterministic, verified). One live physical beat on a printed
"station mat" with a phone camera (the glove reaches into pesto, then mayo, and the mayo tile
flips amber in front of the judges). Live worker taps in `PROTOCOL_ONLY`/`FULL` on the same
screen. Last net: a screen-recorded video of the replay demo. Nothing else is attempted.

Two devices work from this file: the demo laptop (station, rehearsal) and the deck laptop
(slides). Numbers for the deck are in §7. The narration is in §5.

---

## 1. Shopping / gather list (one bag)

- Printed from `data/build/print/` (tracked; also regenerable into `data/markers/`) at **100% scale, matte paper**: mat sheets (`mat_letter_A.png`,
  `mat_letter_B.png` or the A4 pair; corner markers are printed ON the mat), `tool_10_spreader.png`, `tool_11_spreader_2.png`,
  `surface_20_board.png`, `surface_21_board_2.png`, spare `corner_00..03.png`.
- Clear tape, scissors.
- 4 paper cups or bottle caps (bins: pesto, mayo, turkey, bread), 2 plastic knives (spreaders),
  2 index cards (boards), 1 plate or paper square (landing), 1 small box (clean stock).
- **Blue or purple nitrile gloves** (pharmacy). Last resort: a blue sticky note on a fingertip.
- Phone + stand (or a cup to lean it on), phone cable, laptop charger, HDMI/USB-C adapter.

## 2. Timeline (hard stops)

| Time | Demo laptop (hands) | Claude (screen) |
|---|---|---|
| 10:30–11:00 | print, gather, `git pull`, enable Continuity Camera | mat images, scaled station config |
| 11:00–11:30 | tape mat, place props, phone framing check in Photo Booth (then close it) | fallback screen recording |
| 11:30–12:15 | calibrate → tune HSV → **go/no-go 5/5 test** (§4) | threshold fixes from your outputs |
| 12:15–13:00 | lunch | run book final, evidence files |
| 13:00–14:30 | **five clean rehearsals** + failure drill; tap counts on paper; **screen-record run #3 with Cmd+Shift+5 (whole screen, mic on) → save as `data/build/demo_fallback.mov`** | fixes only if a run fails |
| 14:30–15:15 | deck numbers merged, script timed twice | — |
| 15:15–15:45 | pack (§8), pre-flight | — |
| 15:45 | walk; in the room: mat, props, phone, banner FULL check (2 min max) | — |

## 3. Setup commands (demo laptop)

```bash
cd ~/Documents/hackathon/hackathon && source .venv/bin/activate && git pull
python -c "import cv2; print([i for i in range(4) if cv2.VideoCapture(i).isOpened()])"   # camera index
python scripts/calibrate.py --station mat --source 0 --frames 30        # error must be < 3 mm, then:
python scripts/calibrate.py --station mat --source 0 --frames 30 --write
python scripts/tune_hsv.py --source 0                     # sliders until only the glove is white; w = save, q = quit
```

## 4. Go/no-go test (11:45)

```bash
STATION_ID=mat STATION_CAMERA=0 uvicorn src.runtime.app:app
```
Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/inspector`. Banner must read FULL.
Glove into the pesto cup (hold 1 s), out, wait 2 s, into mayo. Five tries.
- **5/5** → the live mat beat is in.
- **< 5/5** → the mat beat is cut; present option 2 only. Do not spend more time on it.

## 5. The two-minute script (what to say, do, and what the screen shows)

Servers (start in this order, leave running all day):
```bash
STATION_REPLAY=scenarios/demo.yaml uvicorn src.runtime.app:app --port 8001   # main show
STATION_ID=mat STATION_CAMERA=0 uvicorn src.runtime.app:app --port 8000      # live mat (if go)
```
Browser tabs in order: `http://127.0.0.1:8001/` · `http://127.0.0.1:8000/` ·
`http://127.0.0.1:8001/inspector` · `data/build/demo_fallback.mp4` (paused at 0:00).
Restart the `:8001` server right before you start (the replay begins at server start).

| Beat | Say | Do | Screen (`:8001`) |
|---|---|---|---|
| 0 | "This is a prep station. Eight things carry allergens: gloves, spreader, board, plate, four shared bins." | — | grid of 8 tiles, quiet |
| 1 | "Ticket 47, pesto sandwich, no restriction. Watch how little happens." | — | tiles amber: gloves, spreader, board. **No alert.** |
| 2 | "Now, same gloves, into the mayo." | **live beat, on `:8000`**: glove into pesto cup, then mayo cup | mayo tile amber: *Shared container — affects all future tickets* |
| 3 | "Ticket 48. Turkey sandwich. Pine-nut allergy." | — | Tier 0 **before any motion**: New gloves / Clean spreader / Mayo container — use sealed backup / Fresh board |
| 4 | "Change gloves, swap the spreader, fresh board, sealed mayo." | — | items tick off one by one; prompt clears; silence |
| 5 | "Rerun it and ignore the prompt: dirty spreader onto the sandwich." | — | Tier 1 STOP, then **HOLD — DO NOT SEND** with the evidence trace and: *This is an observation, not a determination. Confirm with the cook.* |
| 6 | "It doesn't replace the protocol. It checks that the protocol happened." | tap **Cook confirms**, tap **Release** (2 taps) | quiet |

Failure drill (only if asked or if the camera dies): pull the phone; banner → PROTOCOL ONLY —
VISION UNAVAILABLE; bind a restricted ticket on `:8000`; Tier 0 still fires. "A failure that
is part of the script is not a failure."

If `:8001` misbehaves: switch to the fallback video tab and say "this is a recording of the
same run."

## 6. Honesty lines (say them; judges reward them)

- "Observations on the main screen are replayed from a recorded run; the reasoning, alerts,
  and every tap are live."
- "The system never says food is safe. It says what it observed and did not observe."
- "There is no green anywhere on that screen on purpose."

## 7. Numbers for the deck (all from `data/eval/2026-09-12/`)

- 593 automated tests; strict type-checking on 49 core files; 8 import-boundary contracts
  (perception can never import safety code).
- 14/14 scenario fixtures pass, byte-identical across two runs; intervention recall 1.0;
  silent-miss rate 0.
- Four planted violations rejected by the build (import boundary, wall-clock in the core,
  malformed config, prohibited claim word).
- Every alert type resolvable in ≤ 2 taps (Tier 0: 1, Tier 1: 1, Tier 2: 2); add the
  rehearsal counts here: ____ / ____ / ____.
- Perception: deterministic (ArUco frame + colour + geometry), no training data, honesty
  events for occlusion; verified on synthetic video; real-footage gate pending.
- Fallback ladder rehearsed: fixture replay and recorded-log replay produce identical UI.

## 8. Pack list

Mat, tape, cups, knives, cards, plate, box, gloves, phone + stand + cable, laptop at 100%,
charger, adapter, spare markers. Both servers running; four tabs open; video paused.

## 9. Where things are

- **The deck** (3D presentation that hands off to the real display and back): `deck/README.md`
  (start: `cd deck && npm run build && npm run stage` → `http://127.0.0.1:5174/#0`; keys, script,
  fallback drill there). Storyboard and rationale: `deck/PITCH.md`. Numbers in §7 are the ones on
  the receipt scene; the suite is now 533 passed.

- Run book with all beats and the field procedure: `data/build/runbook_B.md`
- Status and evidence: `data/build/status_B.md`, `data/eval/2026-09-12/`
- Marker and mat images: `data/build/print/` (tracked; also regenerable into `data/markers/`) (regenerate with `python scripts/print_markers.py`)
- Station config for the mat: `config/station/mat.yaml` (380 x 230 mm frame; run servers with `STATION_ID=mat`)
- Mat sheets: `data/build/print/mat_letter_A.png` + `_B.png` (or `mat_a4_*`); `python scripts/print_mat.py --paper a4` to regenerate
