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
| P3 Worker interface + `PROTOCOL_ONLY` | `IMPLEMENTED` (→ `VERIFIED` once a teammate measures taps) | `p3_protocol_only_rehearsal.json` (live PROTOCOL_ONLY path), `p3_fallback_ladder.json` (all beats 1–5 on the display from fixture and from a recorded log); alert-copy lint green (`tests/property::test_alert_copy_guard`, `tests/integration/ui/test_copy_lint.py`); ≤ 2 taps mechanically (Tier 0: 1, Tier 1: 1, Tier 2: 2) — **teammate measurement pending** |
| P4 / P5 Perception | `OPEN` → in progress (13:40 EDT, on the user's instruction): pipeline + field scripts + scorer being built and tested on synthetic frames; the P4 gate (precision/recall on 12 annotated clips, occlusion recall ≥ 0.95, nuisance < 1/hr) still needs the recordings — see `runbook_B.md` §Field procedure | hardware check above; `data/eval/2026-09-12/p4_perception_report.json` once clips exist |
| P6 Demo hardening | `PARTIAL` | `data/eval/2026-09-12/p3_fallback_ladder.json`: ladder levels 2 and 3 produce identical UI (live-sampled on the display, plus `test_replay_mode.py`); camera-unplug drill = scenario L replay; **not done: 5 consecutive clean live runs (no live station exists)** |

## Status drift for A to fold in
- `PROJECT_STATE.md` §2: "no git repository" is stale — repo exists with remote `origin`.

## Audit loop (13:20 EDT)
Read-only audit against `26`/`02`/`37`/`39` §6 found 1 blocker, 6 majors, 4 minors — all fixed and
re-verified live: `data/eval/2026-09-12/p3_audit_findings.json`. Final commit `5a38ea9`: 531 tests,
mypy --strict 38 core files, lint-imports 8 kept, 14/14 fixtures deterministic.

## P3 gate statement (12:55 EDT)

`38` §P3 has three clauses. **Two are green, one needs a person:**
1. every alert type resolvable in ≤ 2 taps, measured on a teammate — mechanically ≤ 2 (Tier 0: 1, Tier 1: 1, Tier 2: 2 or 1); **teammate measurement not done** (`runbook_B.md` §Tap-count table is ready to fill);
2. alert-copy lint green — **green** (`tests/property::test_alert_copy_guard`, `tests/integration/ui/test_copy_lint.py`);
3. a complete demo runs in `PROTOCOL_ONLY` with no camera attached — **green** (`p3_protocol_only_rehearsal.json`, `test_app.py`).

So: **P3 IMPLEMENTED, one human measurement from VERIFIED.** There is a shippable, demoable
product with no perception at all; the run book drives it.

## Numbers handed over (convergence §8.2)

| item | value |
|---|---|
| P0 plants rejected | 4 of 4 (+1 UI copy plant) |
| P1 fixtures | 14/14 pass, 14/14 deterministic, IR 1.0, SMR 0.0, hazards 6 |
| Suite | 528 passed; mypy --strict 38 core files; lint-imports 8 kept; ruff clean |
| Tap counts (mechanical) | Tier 0 = 1, Tier 1 = 1, Tier 2 = 2 (or 1 remake); teammate: pending |
| Fallback ladder | level 3 (fixture) and level 2 (recorded log) identical on the display; level 1 N/A |
| `[DEFER]` rows | B63, B64, B65 confirmed absent by grep (`ledger_B.md`) |
| P4 metrics | none — no hardware |
