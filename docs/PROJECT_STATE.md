# Project State

**Operational checkpoint.** Authoritative for **status only** — never for design. Update at
the end of every working session and at every phase gate.

**Last updated:** 2026-09-12 12:10 EDT · **Phase:** P0–P2 VERIFIED, P3 IMPLEMENTED · **Mode:** sole driver

---

## 1. Architectural state
Fully specified, not implemented. All layer boundaries, interfaces, and models are defined
in `docs/architecture/`. Twelve ADRs accepted (`docs/decisions/`). No architectural question
is currently open that blocks P0.

## 2. What has been implemented
Git on `main`, remote `origin = https://github.com/RohanPejaver/hackathon.git`. Harness and
contracts exist and are gate-verified: `pyproject.toml` (39 §2 deps, pydantic pinned 2.13.5,
8 import-linter contracts), `.gitignore`, `requirements.lock`; `src/domain` (types incl. Q1
`ticket_lifecycle`, three epistemic values, headline validators), `src/events` (33-type catalog,
`EventLog` with private reorder buffer, `EventSink`, `GradedEvent` projection); `src/runtime`
(`config.py` loader/validation/checksums/`to_domain`, `clock.py`, `controller.py`, `app.py`
composition root coded against the P1 APIs); `src/ui` (FastAPI + WebSocket server, wire shape,
static HMI shell with vendored Open Props / Phosphor / Archivo / IBM Plex); `config/` (defaults,
profiles, demo station, demo knowledge bundle). P1 packages (`state`, `risk`, `policy`,
`knowledge`, `orders`, `replay`, `scenarios/`) are being written by four concurrent streams.

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
P1 as four concurrent streams on disjoint paths (integration contract in `data/build/openq_B.md`
§CHANNEL and §Sole-driver decisions): S1 reducer (`src/state`), S2 risk + policy + knowledge,
S3 scenarios A–M + `demo.yaml` + replay runner + `scripts/determinism_check.py`, S4 orders.
Then the P1 gate (13 fixtures, determinism, SMR = 0 → `data/eval/<date>/p1_replay_report.json`),
then P3 (`uvicorn src.runtime.app:app` in `PROTOCOL_ONLY`, no camera).

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
Land the four P1 streams, run `pytest -q` + `python scripts/determinism_check.py`, fix only
B-owned failures via repair passes, write `data/eval/2026-09-12/p1_replay_report.json`, then
run the P3 gate from `data/build/runbook_B.md`.

## 9. Evidence that the previous phase is complete
Planning phase: `docs/` contains 29 documents; every architecture layer in `10` has an owner
document; every interface in `22` has a named owner module; every failure mode in `23` maps
to a planned fixture or metric; the architectural audit found and fixed 9
defects (duplicated threshold defaults; unscoped pessimistic closure; missing
`recent_allergen_exposure` state; three undefined interfaces; unmeasured top risk; two
implementation leaks; one premature optimization).

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
