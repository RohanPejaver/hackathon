# Demo Plan

The demo is a **product requirement with architectural consequences**, not a final-day
activity. It is specified here so the architecture is built to support it.

## Physical setup

Folding table. Overhead camera on a fixed mount (calibrated, `config_version` frozen the
night before). Four labeled bins: `pesto`, `mayo`, `turkey`, `bread`. One cutting board, one
spreader, a glove box, a clean-tool rack, a landing zone. A station display showing live
carrier state. Total footprint: one table.

Deliberately: **no crowd, no audio, no network, no lighting requirements beyond ambient.**
The demo's dependencies are a table and a pair of hands.

## Script (2 minutes)

| Beat | Action | System | Purpose |
|---|---|---|---|
| **0** Setup (15s) | Show four carriers, all green | silent | Establish the state display |
| **1** Ticket 47 (25s) | Bind "pesto sandwich, no restriction". Scoop pesto, spread, plate | **Silence.** `gloves`, `spreader`, `board` turn amber | *"95% of the time this is furniture."* Defuses alert-fatigue objection up front |
| **2** The reach (10s) | **Without changing gloves, reach into the mayo tub** | `bin:mayo` flips amber: *"Shared container — PINE_NUT — affects all future tickets"* | **The peak.** Non-obvious, instantly legible |
| **3** Ticket 48 (30s) | Bind "turkey sandwich, PINE_NUT allergy" | Tier 0 **before any motion**: gloves / spreader / **use sealed backup mayo** | Order-awareness; third line is the one that matters |
| **4** Compliance (20s) | Change gloves, swap spreader on camera | Checklist items tick themselves off; carriers green; prompt clears; prep proceeds silently | Reset verification; compliance feels like progress |
| **5** Failure branch (20s) | Rerun 48, **ignore the prompt**, build with the dirty spreader, move to the pass | **Tier 2 HOLD** with the full evidence trace, and the line: *"This is an observation, not a determination. Confirm with the cook."* | Epistemic discipline under failure — demoing your own limits earns trust |
| **6** Close (10s) | — | — | *"It doesn't replace the protocol. It checks that the protocol happened."* |

## Architectural requirements the demo imposes

1. **State display is first-class**, not debug UI. The amber-spread across carriers *is* the
   visualization that makes invisible state visible. Build it in P3, not P6.
2. **Back-contamination must be a plain pathway**, not a special case — beat 2 is only
   convincing if it emerges from the same model as everything else.
3. **Tier 0 must fire at bind, before motion.** Requires the precondition check to be
   synchronous with `TICKET_BOUND`.
4. **Resets must visibly clear the checklist.** Beat 4 is the payoff for beat 3.
5. **`PROTOCOL_ONLY` must be presentable.** If the camera fails on stage, the system
   degrades visibly and Tier 0 still fires — beats 3 and 6 survive without perception.

## What runs live, and what does not

**The demo is live.** A person performs the actions; the camera observes; events, state,
risk and the alert all compute in real time. Target contact-to-alert latency is under 1.5s
(`34`).

| Live during the demo | Configured beforehand |
|---|---|
| Every physical action | Station calibration + homography (frozen, checksummed the night before) |
| Perception -> events | Zone polygons and their contents |
| Taint propagation, pathway search | Allergen taxonomy + ingredient map |
| Tier selection, alert lifecycle | Menu item -> required zones |
| Worker taps and assertions | — |

Nothing in the right-hand column is a shortcut: in a real deployment those are exactly the
things set up once at installation. Say so if asked — the honest answer is stronger than
hedging.

## Determinism under pressure

- Bins, tools, and camera are physically fixed and taped; calibration frozen and checksummed.
- The full demo exists as a scenario fixture (`scenarios/demo.yaml`) that reproduces every
  beat with **zero hardware**. The fallback ladder is:
  `live perception -> recorded log replay -> scenario replay`, all producing identical UI.
- Gate: **5 consecutive clean live runs** before the demo is considered ready (P6).
  **If that gate does not pass, do not demo live.** Run from the recorded log and say
  plainly that you are doing so. A smooth replay beats a live run that stalls, and
  volunteering the substitution costs far less credibility than being caught in one.
- Even with zero working perception, the demo still runs **live** in `PROTOCOL_ONLY`:
  tickets bind live, Tier 0 fires live, the worker resolves live, holds work live. Only
  camera-driven observation is missing. That floor is reached at the end of P3.
- Rehearsed failure drill: unplug the camera mid-run and narrate `PROTOCOL_ONLY`. A failure
  that is part of the script is not a failure.

## Explicitly not in the demo

Multi-station, manager dashboards, POS integration, analytics, evidence video, any claim of
food safety. Each would lengthen the script and weaken the claim.
