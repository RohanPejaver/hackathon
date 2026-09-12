# Workflow: Roadmap, Gates, and Documentation Maintenance

## Status model

| Status | Meaning |
|---|---|
| `VERIFIED` | Capability exists **and** the named evidence artifact proves it |
| `IMPLEMENTED` | Code exists and unit tests pass; gate evidence not yet produced |
| `PARTIAL` | Some sub-capability works; explicitly enumerate what does not |
| `OPEN` | Not started |
| `BLOCKED` | Cannot proceed; name the blocker and its owner |
| `N/A` | Deliberately out of scope; link the decision |

**Code existing is never sufficient for `VERIFIED`.** Each gate below names the artifact.

## Roadmap — vertical slices ordered by architectural dependency

### P0 — Foundations
- **Objective:** The contracts exist and round-trip.
- **Prereqs:** ADRs 0001-0004 accepted.
- **Scope:** repo skeleton + import lint; `domain/` types; event schemas v1;
  `EventLog` with reorder window; config loader + validation; scenario file parser;
  `Clock` injection.
- **Non-goals:** any reasoning, any perception, any UI.
- **Gate -> VERIFIED:** every event type serializes and round-trips; import-lint rejects a
  deliberately planted violation; config validation rejects a deliberately malformed bundle;
  clock-access lint rejects a planted `now()` in `state/`.

### P1 — Reasoning core (no vision) **[the critical phase]**
- **Objective:** The product thesis is provably implemented with zero camera.
- **Prereqs:** P0.
- **Scope:** reducer + full `13` transition table; pathway search; precondition check;
  tier selection; alert lifecycle with dedup/escalation/cooldown; `ReplayRunner`;
  fixtures A-M.
- **Non-goals:** perception, real orders, styled UI.
- **Gate -> VERIFIED:** **all 13 fixtures pass**; property tests green; determinism test
  (each fixture twice, byte-identical) green; SMR = 0 on the suite. Artifact:
  `data/eval/<date>/p1_replay_report.json`.
- **Why first:** the event-log boundary means this needs no hardware, and it is the part
  that is actually novel. If it is not done, nothing else matters.

### P2 — Orders and knowledge
- **Prereqs:** P1.
- **Scope:** `KnowledgeProvider` + bundle; taxonomy closure; `RestrictionNormalizer` with
  mandatory `AMBIGUOUS`; ticket lifecycle + binding; recipe -> required zones.
- **Gate:** scenario G passes end-to-end; `BLOCKED -> BOUND` proven unreachable;
  below-threshold text never yields `RESOLVED`; Tier 0 blocking lists are recipe-scoped, not
  whole-station.

### P3 — Worker interface and `PROTOCOL_ONLY`
- **Prereqs:** P2.
- **Scope:** the three surfaces (`26`); assertion capture -> events; evidence-trace
  rendering; live carrier-state display; `PROTOCOL_ONLY` mode complete.
- **Gate:** every alert type resolvable in <= 2 taps (measured on a teammate, not the
  author); alert-copy lint green; **a complete demo runs in `PROTOCOL_ONLY` with no camera
  attached.**
- **Why this matters:** at the end of P3 there is a **shippable, demoable product with no
  perception at all.** All perception risk is now upside rather than existential.

### P4 — Perception: zones, hands, contact
- **Prereqs:** P3 (so events have somewhere verified to land).
- **Scope:** calibration -> station frame; zone authoring tool; hand/glove tracking; contact
  + dwell + hysteresis -> episodes; occlusion -> epistemic events; health -> `PROTOCOL_ONLY`.
- **Gate:** event-level precision/recall on 12 annotated clips meets targets;
  **occlusion-reporting recall >= 0.95**; live contact events flow into the already-verified
  core; Nuisance Rate < 1.0/hr on the 30-minute normal-prep set. Artifact:
  `data/eval/<date>/p4_perception_report.json`.

### P5 — Perception: carriers and reset verification
- **Prereqs:** P4.
- **Scope:** tool/board tracking; `TOOL_SWAP` / `SURFACE_SWAP`; glove-change detection;
  `TRACK_IDENTITY_SUSPECT` + pessimistic merge; `SURFACE_WIPE` (recorded, non-clearing).
- **Gate:** glove-change recall >= 0.90 on fixtures; scenario D works live; scenario K
  (identity switch) produces a merge, never a silent reassignment.

### P6 — Demo hardening
- **Prereqs:** P5 (or P4 if P5 slips — the demo degrades to operator assertions).
- **Scope:** freeze calibration; `scenarios/demo.yaml`; fallback ladder; failure drills;
  trace polish.
- **Gate:** **5 consecutive clean live runs**; camera-unplug drill rehearsed; all three
  fallback levels produce identical UI.

## Priority ruthlessness

| Priority | Items |
|---|---|
| **Must build** | P0-P4, plus back-contamination (scenario I) and `PROTOCOL_ONLY` |
| **Should build** | P5 glove-change + identity-switch handling; scenario D live |
| **Could build** | Manager surface, audit export, multi-station read-only aggregation |
| **Explicitly defer** | Rag/wipe-cloth perception, wash-cycle detection, evidence video clips, any ML risk model, POS/delivery adapters, authentication, mobile app, analytics |

## ADR threshold

Write an ADR when a decision: (a) changes a layer boundary or an interface in `22`;
(b) changes what the system claims or refuses to claim; (c) changes an invariant in `11`;
(d) introduces a core-group dependency; (e) would be expensive to reverse after P2; or
(f) was contested and the reasoning would otherwise be lost.

**Do not** write ADRs for naming, file placement, formatting, or any choice reversible in
under an hour.

## Documentation maintenance protocol

| Change | Required updates |
|---|---|
| New/changed event type | `12`, affected fixtures, schema version bump, migration note |
| New/changed state transition | `13`, state-transition tests, possibly `14` |
| Changed reset validity | `14` + **ADR** (safety semantics) |
| New interface or signature change | `22` **only** (never restate elsewhere) + dependent docs' references |
| New failure mode | `23` + a fixture or metric (the meta-test enforces this) |
| Changed threshold/window | `31` defaults table + affected fixtures |
| New claim the system makes | `02` + an alert-copy lint case |
| Any phase status change | `PROJECT_STATE.md` + the evidence artifact link |

**Staleness detection:** every doc carries a `last-reviewed` line. CI warns on any
`architecture/` doc older than the most recent ADR affecting its area. A doc contradicting
code is a **defect ticket**, not a doc edit — decide which is wrong first.

**Conflict resolution precedence:** `docs/CLAUDE.md` > ADRs (most recent) > `product/` >
`architecture/` > `engineering/` > code comments. `PROJECT_STATE.md` is authoritative for
**status only**, never for design.
