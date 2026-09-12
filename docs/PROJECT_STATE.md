# Project State

**Operational checkpoint.** Authoritative for **status only** — never for design. Update at
the end of every working session and at every phase gate.

**Last updated:** 2026-09-12 12:55 EDT · **Phase:** P0–P2 VERIFIED, P3 IMPLEMENTED (teammate tap measurement pending), P4–P6 blocked on hardware · **Mode:** sole driver

---

## 1. Architectural state
Fully specified, not implemented. All layer boundaries, interfaces, and models are defined
in `docs/architecture/`. Twelve ADRs accepted (`docs/decisions/`). No architectural question
is currently open that blocks P0.

## 2. What has been implemented
Everything on the P0→P3 cut line (`39` §9), in one process, with no camera:
`src/domain` + `src/events` (contracts, 33-type catalog, log with private reorder buffer,
confidence-free `GradedEvent`); `src/state` (full `13` transition table); `src/knowledge`
(closure, provider); `src/risk` (recipe-scoped preconditions, backward pathway search with
reset-breaks-path); `src/policy` (tiers per `15` + ADR-0005, `alert_key` dedup, escalation at
COMPLETE, cooldown, copy templates); `src/orders` (deterministic normalizer with mandatory
AMBIGUOUS, intake, lifecycle, manual/fixture sources); `src/replay` (loader, runner, assertion
vocabulary) with `scenarios/` A–M + `demo.yaml`; `src/runtime` (config loader/validation/
checksums, clocks, `RuntimeController`, composition root with REPLAY feed); `src/ui` (FastAPI +
WebSocket at 5Hz, worker display with the three `26` surfaces, carrier grid, evidence trace,
read-only inspector, vendored assets, HMI styling with no green). `config/` holds the demo
station and knowledge bundle. `src/perception/` is empty by decision (no hardware).

## 3. What has been verified
| Phase | Status | Evidence |
|---|---|---|
| P0 Foundations | `VERIFIED` | `data/eval/2026-09-12/p0_gate_report.json`: ruff/mypy --strict/lint-imports/pytest green; planted `state→perception` import, planted `datetime.now()` in `state/`, malformed bundle, and claim word in `policy/copy.py` each rejected then reverted |
| P1 Reasoning core | `VERIFIED` | `data/eval/2026-09-12/p1_replay_report.json` — 14/14 fixtures pass, byte-identical twice, IR 1.0, SMR 0.0; 526 tests; strict mypy; lint-imports |
| P2 Orders & knowledge | `VERIFIED` | scenario G end to end; `BLOCKED→BOUND` unreachable proof; normalizer never RESOLVED below threshold; recipe-scoped Tier 0 |
| P3 Worker interface | `IMPLEMENTED` | `data/eval/2026-09-12/p3_protocol_only_rehearsal.json` — full demo path live in PROTOCOL_ONLY with no camera; teammate tap-count measurement pending |
| P4 Perception: zones/contact | `BLOCKED` — no camera, no annotated fixtures (`data/build/status_B.md` §Hardware check) | — |
| P5 Perception: carriers/resets | `BLOCKED` — same | — |
| P6 Demo hardening | `OPEN` | — |

## 4. What remains
All of P0-P6 (`engineering/38-workflow.md`).

## 5. Currently being worked on
Convergence: read-only audit of the worker interface against `26`/`02`/`37`/`39` §6 (findings
become fixes or scenario fixtures), then the teammate tap-count measurement (the only P3 gate
clause a single driver cannot close).

## 6. Recent decisions
ADR-0001 through ADR-0012, all accepted 2026-09-12. The load-bearing three: **0001**
(event log as a pure fold — everything else descends from it), **0005** (uncertainty lowers
the tier, never the bar), **0008** (carriers hold taint, not dishes).

## 7. Read before making changes
1. `docs/CLAUDE.md` — conduct (pre-existing, authoritative)
2. `docs/product/01-thesis.md` — frozen thesis
3. `docs/product/02-safety-boundaries.md` — what may and may not be claimed
4. `docs/architecture/10-system-overview.md` — the boundary
5. `docs/architecture/22-interfaces.md` — before touching any subsystem
6. `docs/engineering/38-workflow.md` — gates and the doc-maintenance protocol

## 8. Single most appropriate next action
**Measure taps on a teammate** (Tier 0, 1, 2 from `data/build/runbook_B.md`) and record the
numbers in `data/build/status_B.md`; that closes P3 → `VERIFIED`. Then, if a camera and the 12
annotated clips appear, start P4 in `src/perception/` against `21` — nothing else is blocked.

## 9. Evidence that the previous phase is complete
`data/eval/2026-09-12/`: `p0_gate_report.json` (four planted violations rejected),
`p1_replay_report.json` (14/14 fixtures, byte-identical twice, IR 1.0, SMR 0.0),
`p3_protocol_only_rehearsal.json` (full demo path live with no camera),
`p3_fallback_ladder.json` (levels 2 and 3 identical on the display). Suite: 528 passed;
`mypy --strict` on 38 core files; `lint-imports` 8 contracts kept; ruff clean.
Ledger: `data/build/ledger_B.md` (62/65 SATISFIED with file:line), `ledger_A.md` summary.

## 10. Unresolved assumptions
Tracked, not hidden. Each is config or an experiment, never a silent code choice.

| # | Assumption | Risk if wrong | Resolution |
|---|---|---|---|
| A1 | `max_hops = 3` is a reasonable transfer bound | Over/under-alerting | Config; EXP-001 |
| A2 | Ingredient bins stay in fixed, calibrated positions | Silent zone mismatch | Config checksum + startup validation; operational rule |
| A3 | Glove changes are visually detectable at `OBSERVED` grade | Tier 0 checklists cannot self-tick; demo beat 4 weakens | EXP-004; fallback is operator assertion |
| A4 | A cook will tap to bind a ticket | Binding fails, Tier 0 never fires | Mirrors existing KDS gesture; validate with a real operator |
| A5 | 2D overhead view separates reach-in from reach-over adequately | False contacts -> Tier 0 noise | `t_dwell` tuning; EXP-002 |
| A6 | Pessimistic closure does not fire so often it becomes noise | Tier 0 fatigue — the central adoption risk | Measure at P4 against the normal-prep set; tune `t_stale` |

**A6 is the most important open risk in the project.** It is the one that would make the
system annoying rather than wrong, and annoying is the failure mode that gets a safety system
unplugged.
