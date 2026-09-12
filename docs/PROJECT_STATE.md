# Project State

**Operational checkpoint.** Authoritative for **status only** — never for design. Update at
the end of every working session and at every phase gate.

**Last updated:** 2026-09-12 · **Phase:** P0 contract review BLOCKED · **Mode:** Device A ingestion complete

---

## 1. Architectural state
Fully specified, not implemented. All layer boundaries, interfaces, and models are defined
in `docs/architecture/`. Twelve ADRs accepted (`docs/decisions/`). No architectural question
is currently open that blocks P0.

## 2. What has been implemented
No runtime implementation yet. Git exists on `main` with remote
`origin = https://github.com/RohanPejaver/hackathon.git`. Device A completed the document
spine review, a 99-row requirements inventory, and a 33-callable registry transcription:
`../data/build/ledger_A.md`, `../data/build/contracts.md`. These are planning artifacts,
not implemented contracts. No FREEZE-1 or HANDSHAKE-2 has been published.

## 3. What has been verified
No phase gates have run or passed. No replay, determinism, install, metric, or
planted-violation evidence exists. Contract review findings are in
`../data/build/openq_A.md`; these do not justify VERIFIED.

| Phase | Status | Evidence |
|---|---|---|
| P0 Foundations | `BLOCKED` | Contract registry owner: resolve Q1–Q4 in `../data/build/openq_A.md` |
| P1 Reasoning core | `OPEN` | — |
| P2 Orders & knowledge | `OPEN` | — |
| P3 Worker interface | `OPEN` | — |
| P4 Perception: zones/contact | `OPEN` | — |
| P5 Perception: carriers/resets | `OPEN` | — |
| P6 Demo hardening | `OPEN` | — |

## 4. What remains
All of P0-P6 (`engineering/38-workflow.md`).

## 5. Currently being worked on
Device A scope: P0–P2 and joint integration through P3. Ingestion/ledger work is
complete. EventLog and policy contract freeze workstreams are blocked by missing or
incomplete input contracts (Q1–Q4). Subagents cannot launch before FREEZE-1.
Device B harness/content work can continue independently; B has no reachable task on
this host, so the channel notice is recorded in `../data/build/openq_A.md`. B status
and delivery acknowledgment are not confirmed. P4/P5 remain B-owned if hardware exists;
P6 requires a live station and is out of scope for this code session.

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
**Specification owner resolves the pre-freeze contract gaps with Device B.** Review
`../data/build/openq_A.md` Q1–Q4 and approve an authoritative amendment for lifecycle
inputs, draft/reorder commitment, event payloads, and snapshot shape. A may not edit
locked design docs or invent missing subsystem signatures. Then implement P0, verify
its gates, publish FREEZE-1, and dispatch the disjoint P1 streams. Do not begin reducer
logic before that freeze. Git initialization is already complete.

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
