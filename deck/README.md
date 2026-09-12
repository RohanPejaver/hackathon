# Deck — HackCMU 2026 (3 minutes)

The pitch is one page: a 3D model of the real station (`config/station/demo.yaml`), keyboard
driven, that hands off to the **real worker display** in REPLAY mode and comes back. Plan,
storyboard and script: `PITCH.md`.

## Start (deck laptop, before walking to the room)

```bash
cd deck && npm run build && npm run stage        # http://127.0.0.1:5174/#0  (serves dist/, controls the replay on :8001)
```

Open `http://127.0.0.1:5174/#0` in Chrome, press `F` for fullscreen, `H` to hide the HUD,
then `Esc` to be on scene 0. Press `→` once and `←` once so every scene's shaders are warm.
Requires the repo's `.venv` (`uv venv --python 3.11 .venv && uv pip install -e '.[dev]'`).

Dev: `npm run dev` (http://localhost:5173) with `npm run stage` running for the API.

## Hosted copy (Vercel)

The deck is a static Vite build. Deploy from the `deck/` directory (Vercel project root =
`deck`, framework Vite, output `dist`; `vercel.json` sets this). A hosted copy has no product
server, so scene 4 plays the recording of the real display (`V`) by default; `S` steps the
stills. `R`, `L` and `P` only work on the laptop that runs `npm run stage`.

```bash
cd deck && npx vercel login && npx vercel --prod
```

## Keys

| key | does |
|---|---|
| `→` `Space` | next scene (in the demo, stills mode: next still) |
| `←` | previous |
| `0`–`9` | jump to scene (`4` = demo) |
| `Esc` / `Home` | scene 0 |
| `B` | backup scenes (architecture, built/pending, evaluation, failure modes, perception, privacy, next); `→` walks them |
| `F` | fullscreen · `H` HUD on/off |
| in the demo: `R` | restart the replay from 0 (server restart, ~2 s) |
| in the demo: `V` | local recording of the same run (`public/fallback/demo.webm`) |
| in the demo: `S` | stills of the six decisive frames; `→`/`←` step |
| in the demo: `L` | live mat display on `:8000` (only if the go/no-go in `DEMO_PLAN.md` §4 passed) |
| in the demo: `P` | let the mouse into the product (for live taps); click the top edge to get keys back |
| in the demo: `Z` | zoom the product 1.0 → 1.2 → 1.35 for a low-resolution projector |

Entering scene 4 restarts the replay server so the fixture clock starts at 0 on the keypress.
The product's own banner says **REPLAY**. Say so.

## Script (target 2:45; ~280 spoken words outside the demo + the 26 s replay)

**0 · 0:00** *(let the frame sit one second)* "A cook reaches from the pesto into the shared
mayo. Ten minutes later, someone with a pine-nut allergy orders a turkey sandwich."

**1 · 0:10** "The allergy is on a different ticket. There's a reset protocol — new gloves, clean
tool — but nothing checks it happened, and nothing knows the mayo is now a pine-nut carrier."

**2 · 0:25** "The obvious fix is a camera that recognizes pesto. Wrong problem. These sequences
look identical frame by frame; they differ only in what happened *between* two contacts. Time,
order, and what counts as a reset."

**3 · 0:40** "So we built the thing that tracks that. Sequence keeps a live model of what every
glove, tool, surface and shared container is carrying, and checks the reset happened before a
restricted ticket starts. Watch."

**4 · 0:50 → press `→`** "Observations here are replayed from a recorded run; the reasoning,
alerts and every tap are live." *(the replay runs in 17.5 s; speak over it, do not wait)*
+0:01 "Ticket 47, pesto sandwich, no restriction. Gloves, spreader, board go amber. No alert."
· +0:04 "Same gloves, into the mayo." **beat** · +0:06 "Ticket 48, pine-nut allergy. Before any
motion: new gloves, clean spreader, fresh board, sealed backup mayo." · +0:08 "It ticks itself
off." · +0:14 "Rerun it, ignore the prompt, dirty spreader." · +0:17 "Hold. Do not send. *An
observation, not a determination. Confirm with the cook.*" Then press `S` and step the six
stills if you want to linger on any frame.

**5 · 1:45** "Three decisions. Perception only says *a hand entered zone 7* — identity comes from
the station map, not from recognizing food. Everything after the log is a pure fold, so the
same log replays byte-for-byte. And a wipe is not a reset — a cloth moves protein, it doesn't
remove it."

**6 · 2:10** "Fourteen scenario fixtures pass and replay byte-identical. Zero silent misses. We
planted four violations — a wall clock in the core, a perception import, the word *safe* in an
alert — the build rejected every one."

**7 · 2:25** "This is not a vision model with a UI. Pull the camera and it still fires the reset
prompt on every restricted ticket — a supported mode, not an error. Uncertainty lowers the
tier, never the bar."

**8 · 2:38** "Every allergy protocol in every kitchen is a checklist nobody verifies. It doesn't
replace the protocol. It checks that the protocol happened."

**If a rehearsal runs past 2:50, cut in this order:** (1) scene 6's "We planted four
violations…" sentence — the numbers stay on screen; (2) scene 2's last sentence "Time, order,
and what counts as a reset."; (3) the demo's +0:24 line — the checklist ticking is visible.

## If the demo breaks

- The product opens with `?stage=1`: a CSS-only presentation view (no top bar, no observation column, no trace timestamps, bigger tickets). Drop the parameter to show the full display.
- Iframe black or frozen: `R` (restart, ~2 s). Still black: `V` — "this is a recording of the
  same run" — and keep the script. Or `S` and step the six stills with `→`.
- Wrong scene: press its number. Lost: `Esc`.
- Keys stop working: the product iframe has focus — click the very top edge of the screen.

## Honesty lines (say them; the deck shows them)

- REPLAY is on the product's own banner; the fixture is `scenarios/demo.yaml`.
- Numbers are from `data/eval/2026-09-12/` on the scenario suite, not a kitchen.
- Perception is verified on synthetic frames; the real-footage gate is pending (backup scene).
- The reveal slide says "allergen-free order" in green at the team's direction. The product itself never uses the word or the colour; if a judge asks, the answer is: the customer's order is allergen-free, the system only reports what it observed.

## Regenerate fallback assets

```bash
npm run capture      # restarts the replay, records 30 s of the real display -> public/fallback/demo.webm + still-1..6.png
```
