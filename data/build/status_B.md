# Status — Device B (Shell & Surface)

Status vocabulary per `docs/engineering/38-workflow.md`. A folds this into `PROJECT_STATE.md`; B never edits that file.

**Session start (T+0):** 2026-09-12 06:34 EDT · FREEZE-1 expected ~07:34 · HANDSHAKE-2 expected ~08:04

## Hardware check (BUILD_B §2.4) — done 06:36 EDT

| item | present? | evidence |
|---|---|---|
| 1. Mounted overhead camera | **NO** | `system_profiler SPCameraDataType` returns no devices; no USB camera enumerated |
| 2. Printed ArUco markers | unverifiable from this machine; **treated as NO** | — |
| 3. Calibrated station (table, 4 bins, board, spreader, glove box, rack) | unverifiable from this machine; **treated as NO** | — |
| 4. 12 annotated event-level clips + occlusion intervals + 30 min normal prep | **NO** | no `data/` in repo; no annotation files anywhere under `~/Documents/hackathon`, `~/Downloads`, `~/Desktop`, `~/Movies` |

**Scope decision:** P0 harness clauses + **P3 in full** + all content. **P4, P5, P6 are `OPEN` — blocked on hardware (items 1 and 4 missing).** Nothing that requires a camera will be built. Stream B4 is not dispatched. `39` §9: P0–P3 is the product; perception is upside.

## Phase status

| Phase | Status | Evidence |
|---|---|---|
| P0 (B's clauses: harness, lints, scaffold, packaging) | `OPEN` | — |
| P3 Worker interface + `PROTOCOL_ONLY` | `OPEN` | — |
| P4 Perception: zones/contact | `OPEN` — **BLOCKED on hardware** (no camera, no annotated fixtures) | hardware check above |
| P5 Perception: carriers/resets | `OPEN` — **BLOCKED on hardware** | hardware check above |
| P6 Demo hardening | `OPEN` — B's share (run book, fallback ladder rehearsal) tracked under P3 | — |

## Status drift for A to fold in
- `PROJECT_STATE.md` §2: "no git repository" is stale — repo exists with remote `origin`.
