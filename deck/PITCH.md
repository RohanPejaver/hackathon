# HackCMU 2026 pitch — plan, storyboard, script

Judged 4:00 pm, 2026-09-12. 3 minutes, presentation + demo. Track: **Food**.
Everything below is grounded in `docs/`, `data/eval/2026-09-12/`, and `DEMO_PLAN.md`.
Nothing is claimed that the repo does not evidence. Where a thing is replayed, simulated,
or pending, the deck says so on screen.

## A. Presentation thesis

The pitch is one continuous shot of one prep station, seen from above — the exact view the
overhead camera has, built from the real zone polygons in `config/station/demo.yaml`. The
audience watches a single reach (pesto → mayo) that no ticket, no POS, and no person tracks.
The camera then drops *inside* the system to show what it actually reasons about — not food,
but an ordered log of contacts between carriers, with taint that transfers on contact and is
cleared only by a real reset. The real product takes over the screen for the demo, driven by
the verified replay fixture, with REPLAY printed on its own banner. Then the same station
becomes the architecture diagram. The final frame is the opening frame, with the pathway the
system found drawn on it.

## B. Recall identity

**"The station that remembers what touched what."**
Signature image: **pesto in the mayo.** Judges should say "the pesto-in-the-mayo one."
Working product name for the deck: **Sequence** (bounded *backward* pathway search;
*back*-contamination). It is one constant in `deck/src/content.jsx`; change it if the team
has a name.

## C. Visual metaphor

The station itself. One persistent 3D object through every scene; it is literally the config
the product runs on (1200 × 600 mm, bins in the back row, board and landing in front, tool
rack, clean stock, glove dispenser, wash). Amber is the only accent: it is taint, exactly as
on the product's carrier grid. There is no green anywhere, for the same reason the product
has none (`02`). The camera moves only when the argument moves: overhead (what the camera
sees) → low, inside the station (what the reasoning holds) → back overhead (the pathway).
Why it fits: the product's core claim is that risk lives in the *order of contacts between
physical carriers*, not in any frame. A persistent physical station with taint hopping between
objects is that claim made visible.

## D. Storyboard (target 2:45)

| t | Beat | Judge doubt removed | On screen | Spoken (near-exact) | Proof |
|---|---|---|---|---|---|
| 0:00 | Intrigue | "Why should I care?" | Overhead station, dark. A gloved hand goes pesto → mayo. Headline: **One reach. Every ticket after it.** | *(one-second pause)* "A cook reaches from the pesto into the shared mayo. Ten minutes later, someone with a pine-nut allergy orders a turkey sandwich." | thesis §signature capability |
| 0:10 | Failure | "Isn't there already a protocol?" | Ticket cards: #47 pesto (no restriction), #48 turkey, PINE NUT. Mayo tub sits between them, amber. **No ticket knows. No one tracks it.** | "The allergy is on a different ticket. The cook did nothing wrong on theirs. There *is* a reset protocol — new gloves, clean tool — but nothing checks that it happened, and nothing knows the mayo is now a pine-nut carrier." | thesis, 03 §I |
| 0:28 | Insight | "Just detect pesto with a camera?" | One contact chain played four times; only the gap changes: TOOL SWAP / WIPE / 40 s OFF CAMERA / nothing. **The risk isn't in any frame. It's in the order of contacts.** | "The obvious fix is a camera that recognizes pesto. Wrong problem. These four sequences look identical frame by frame. They differ only in what happened *between* two contacts. Time, ordering, and what counts as a reset are the whole problem." | thesis §core problem, ADR-0007 |
| 0:45 | Reveal | "What is it?" | Name + one line: **keeps a live model of what every glove, tool, surface and shared container is carrying — and checks the reset actually happened before a restricted ticket starts.** | "So we built the thing that tracks that. [Name] keeps a live model of what every glove, tool, surface, and shared container is carrying, and checks the reset actually happened before a restricted ticket starts. Watch it." | thesis one sentence |
| 0:55 | Demo | "Does it work?" | The real worker display, full screen, REPLAY on its own banner. Replay restarts on the keypress. | Script in §F. **Magic moment at +0:06**: the mayo tile flips amber, *Shared container — affects all future tickets*. Stop talking. | `p3_fallback_ladder.json` |
| 1:50 | How | "Why was this hard?" | Station becomes a 3-layer diagram: **camera sees geometry, not food** → **append-only observation log; everything after it is a pure fold** → **backward pathway search with reset semantics → tier**. | "Three decisions. Identity comes from the station map, so perception only has to say *a hand entered zone 7* — closed-set geometry, no food recognition. Everything after the log is a pure deterministic fold, so the same log replays byte-for-byte. And risk is a bounded backward search over the contact graph where a wipe is not a reset — because a shared cloth moves protein, it doesn't remove it." | 10, 14, 15, ADR-0001/0007/0009 |
| 2:15 | Receipt | "Is this real?" | Three numbers: **14/14** scenario fixtures byte-identical twice · **0** silent misses, recall 1.0 · **4/4** planted violations rejected by the build. Line: *No SAFE value exists in any enum.* | "Fourteen scenario fixtures — direct, multi-hop, back-contamination, wipe, occlusion, camera fault — pass and replay byte-identical. Zero silent misses. And we planted four violations — a wall clock in the core, a perception import, the word *safe* in an alert — and the build rejected every one." | `p1_replay_report.json`, `p0_gate_report.json` |
| 2:35 | Differentiation | "Isn't this a vision model with a UI?" | **Unlike a food classifier, it never looks at food. Unlike a learned risk model, every alert is a rule chain a cook can dispute in one tap.** Sub-line: *The whole demo runs with the camera unplugged.* | "This is not a vision model with a UI. Pull the camera and it still fires the reset prompt on every restricted ticket — that's a supported mode, not an error. Uncertainty always lowers the tier; it never lowers the bar." | ADR-0003/0005/0011 |
| 2:48 | Implication | "So what?" | Back to the opening overhead frame; the pathway pesto → gloves → mayo → #48 draws itself. **It doesn't replace the protocol. It checks that the protocol happened.** | "Every allergy protocol in every kitchen is a checklist nobody verifies. It doesn't replace the protocol. It checks that the protocol happened." | 37 §Script beat 6 |

The trimmed, timed spoken script with a cut order is `README.md` §Script. Cut from the pitch (kept in backup): concurrency (F), ambiguous restriction (G), tap counts,
perception internals, privacy, latency targets.

## E. Technical-difficulty strategy

Surface exactly three things, each as constraint → choice → consequence:
1. **Identity from configuration, verb from perception** (ADR-0007). Converts open-set food
   recognition into closed-set geometry. Consequence: no training data in the safety path.
2. **Pure fold over an append-only log** (ADR-0001). Consequence: deterministic replay by
   construction, evidence trace for free, the demo has a hardware-free fallback that is the
   *same code path* (`REPLAY` mode replaces layers 1–4 only).
3. **Pathway search with reset semantics and epistemic grading** (14, 15, ADR-0005/0009).
   Consequence: wipe ≠ reset, occlusion degrades to an 8-second prompt, weak evidence can only
   reach Tier 0. This is what another team cannot rebuild tonight.

Not surfaced verbally: ArUco/HSV perception (verified on synthetic frames only), FastAPI,
pydantic, import-linter — except "the build rejects a perception import", which is a proof.

## F. Demo strategy

- **Starting state**: real worker display (`src/ui`) in an iframe, `STATION_REPLAY=scenarios/demo.yaml`
  on `:8001`. Pressing → into the demo scene calls the stage server, which restarts uvicorn so
  the replay clock starts at 0 on the keypress. The product's own banner reads **REPLAY**.
- **Action/narration** (26 s of replay, ~55 s of speech):
  +0:02 "Ticket 47, pesto sandwich, no restriction. Watch how little happens — gloves, spreader,
  board go amber. No alert." · +0:06 "Same gloves, into the mayo." **[silence]** · +0:09 "Ticket
  48. Turkey. Pine-nut allergy. Before any motion: new gloves, clean spreader, fresh board — and
  *use the sealed backup mayo*." · +0:12–16 "Change gloves, swap the tool, fresh board, sealed
  mayo — it ticks itself off." · +0:20 "Rerun it and ignore the prompt: dirty spreader onto the
  sandwich." +0:22 Tier 1 STOP · +0:25 **HOLD — DO NOT SEND**, evidence trace with the absence
  line, *This is an observation, not a determination. Confirm with the cook.*
- **Honesty line, said out loud**: "Observations on this screen are replayed from a recorded
  run; the reasoning, alerts, and every tap are live."
- **Optional live mat beat** (`L` key swaps the iframe to `:8000`) only if the 5/5 go/no-go in
  `DEMO_PLAN.md` §4 passes on the demo laptop.
- **Fallback, one key each**: `V` plays the local recording (`deck/public/fallback/demo.webm`,
  generated by `npm run capture` from the real display); `S` steps through stills of the
  decisive frames. Either reaches the magic moment in under ten seconds.

## G. Visual design system

- **Type**: Space Grotesk 700/500 for headlines (clamp 56–112 px), Inter 400–600 for evidence
  and labels, IBM Plex Mono only inside the product. Scale: 12 / 16 / 22 / 32 / 56 / 88 / 120.
- **Palette**: ground `#07090c`, ink `#e8ebef`, muted `#8a93a0`, **amber `#f0a52e`** (taint,
  the only accent; identical to the product), red `#ff5340` (hold only), blue `#62b1ff`
  (annotation, sparingly). No green, no gradients, radius ≤ 3 px.
- **3D**: matte dark steel table, bins as open boxes, board, landing, rack. No textures, no
  HDRI fetch (procedural `Lightformer` environment), no postprocessing. One key light, one
  soft fill, contact shadows.
- **Camera**: named poses (overhead, three-quarter, low-inside, diagram, overhead-close).
  Damped lerp, ~0.9 s, only on scene change. Never idles.
- **Motion**: only causal — hand travels, taint transfers on contact, pathway draws in order,
  checklist ticks. No drift, no particles, no text flying.
- **UI**: HTML overlay per scene, three levels: headline, evidence, tertiary label. Most scenes
  ≤ 12 words. Product iframe is unstyled — it is the product.
- **Annotation**: `Html` labels anchored to carriers, monospace uppercase micro-labels, amber
  when tainted.

## H. Build plan (deck/)

```
deck/
  package.json, vite.config.js, index.html
  public/fonts/*           vendored Space Grotesk + Inter (no network)
  public/fallback/         demo.webm + still-*.png from `npm run capture`
  src/main.jsx             mount
  src/App.jsx              scene state machine, keyboard, overlay + canvas
  src/content.jsx          every word on screen, per scene (single source of truth)
  src/scenes.js            scene list, camera poses, station animation keyframes
  src/Station.jsx          the 3D station (from config/station/demo.yaml geometry)
  src/Overlay.jsx          headline / evidence / label layers, demo iframe, fallback
  src/styles.css           type scale, palette
  tools/stage.mjs          static server for dist/ + POST /api/replay/restart (spawns uvicorn)
  tools/capture.mjs        Playwright (system Chrome): restart replay, record webm + stills
```

Keys: `→`/`Space` next · `←` prev · `0-9` jump · `R` restart replay · `V` video fallback ·
`S` stills fallback · `L` live mat (`:8000`) · `B` backup scenes · `Esc` reset to scene 0.

## I. Risks

| Risk | Mitigation |
|---|---|
| Replay clock starts at server start, not scene entry | Stage server restarts uvicorn on scene entry (`R` re-arms) |
| iframe WebSocket fails / port busy | `V` video, `S` stills, both local; presenter script has the line |
| Product display too dense at projector distance | Deck is 1920×1080; iframe is full-bleed; magic moments are the big amber tiles and the bottom surface, both large |
| Time overrun | Script targets 2:45; backup content is out of the main path |
| Overclaiming | Every number is from `data/eval/2026-09-12/`; perception is described as "verified on synthetic frames"; the REPLAY banner is the product's own |
| Name invented for the pitch | One constant; flagged here |
| WebGL hitch on first scene | All geometry is primitive; a dev run before stage warms the shader cache |

## Self-critique

- **Weakest beat: Insight (0:28).** Four chains is a lot to read in 15 s. Fix: one chain that
  plays four times with only the gap changing, and the headline carries it.
- **The demo is a replay, not live.** Judges will notice REPLAY. Better to say it first than be
  caught; the honesty line is in the script, and PROTOCOL_ONLY taps are genuinely live if the
  presenter binds a ticket on the display. The live mat beat is upside only.
- **"Sequence" is our invention.** Flagged; one-line change.
- **The receipt numbers are on fixtures, not real kitchens.** Said as "on the scenario suite";
  no nuisance-rate or perception number is shown because none was measured on real footage.
- **3D risk**: the station must be legible in one second. Labels on every carrier; the table is
  the only thing on screen; the hand is the only thing that moves.
