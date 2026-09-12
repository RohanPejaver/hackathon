# Status — sole driver (Device A stopped at FREEZE-1; B owns the whole tree)

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

## CHANNEL (no message channel exists; A reads this on pull)

- **07:05 EDT** B read `openq_A.md`. Answers to Q1–Q8 are in `openq_B.md` §CHANNEL. B is the
  early publisher of the wire shape: `src/ui/wire.py` → `src/ui/static/mock/snapshot.schema.json`
  + `snapshot.example.json`. **A: do not publish a competing `snapshot.*`; conform.**
- FREEZE-1 protocol: B checks `data/build/FREEZE-1.json` after every `git pull --rebase`.
  Until it exists B builds `runtime/` against its own reading of `11 12 13 16 22`.
- Harness landed at `e4116d3`: scaffold (A's packages exist, empty), `pyproject.toml` with 8
  import-linter contracts (`lint-imports` green; planted `state→perception` import rejected by
  `tests/integration/meta`), `.gitignore` (`data/*` + `!data/build/` + `!data/eval/` — the
  literal `data/` form cannot re-include children, as A also noted). `uv venv --python 3.11 .venv`
  then `uv pip install -e '.[dev]'`.

## 07:40 EDT — Device A stopped (credits). B is the sole driver.
- All ownership restrictions lifted except `docs/` (read-only; `PROJECT_STATE.md` now B's).
- A's artifacts adopted as-is: `src/domain`, `src/events` (FREEZE-1 @ 76f02c8), `contracts.md`,
  `ledger_A.md` (99 rows), `openq_A.md` rulings Q1–Q8, `tests/property/test_architecture.py`.
- **P0 VERIFIED** at `e010f09`/`47cbfd1`: `data/eval/2026-09-12/p0_gate_report.json`.
- Wire shape decision: A's `DisplayPayload` (`state_summary` + `interventions`) is the core of the
  snapshot verbatim (it is generated from the real types, so live == mock byte-for-byte); B adds a
  `runtime` block (clock, health, log tail, zones, menu). `src/ui/wire.py` is the schema source.
- P1 dispatched 07:50 as four concurrent streams on disjoint paths: S1 reducer (`src/state`),
  S2 risk+policy+knowledge, S3 scenarios A–M + demo + replay runner + determinism script,
  S4 orders (normalizer, intake, sources). Integration contract is in each packet and mirrored in
  `openq_B.md` §P1 contract.

## Phase status (updated 12:00 EDT)

| Phase | Status | Evidence |
|---|---|---|
| P0 Foundations | `VERIFIED` | `data/eval/2026-09-12/p0_gate_report.json` |
| P1 Reasoning core | `VERIFIED` | `data/eval/2026-09-12/p1_replay_report.json`: 14/14 fixtures (A–M + demo) pass, each byte-identical across two runs, IR = 1.0, SMR = 0.0; `pytest -q` 526 passed; `mypy --strict` on 38 core files; `lint-imports` 8 kept |
| P2 Orders & knowledge | `VERIFIED` | scenario G end to end (`G-ambiguous-restriction` passes: BLOCKED, bind refused, silence); `BLOCKED→BOUND` unreachable proof in `tests/unit/orders/test_lifecycle.py`; below-threshold text never RESOLVED (hypothesis); Tier 0 lists are recipe-scoped (`test_tainted_pesto_bin_is_not_in_a_turkey_sandwich_checklist`) |
| P3 Worker interface + `PROTOCOL_ONLY` | `IMPLEMENTED` | `data/eval/2026-09-12/p3_protocol_only_rehearsal.json`: full demo path driven live through the display with no camera; three surfaces + carrier grid + trace + inspector verified; **teammate tap-count measurement not yet done** |
| P4 / P5 Perception | `BLOCKED` — no camera, no annotated fixtures | hardware check above |
| P6 Demo hardening | `OPEN` | fallback ladder rehearsal waits on `scenarios/demo.yaml` (S3) |

## Status drift for A to fold in
- `PROJECT_STATE.md` §2: "no git repository" is stale — repo exists with remote `origin`.
