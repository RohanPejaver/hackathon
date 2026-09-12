# HANDOFF BUNDLE — INTERFACE

Generated 2026-09-12 05:19. Everything below is the project specification.
Your kickoff prompt is in `docs/engineering/40-team-split.md`, included here.

**Read order:** PROJECT_STATE -> product/01-thesis -> your architecture docs ->
engineering/38-workflow. Do not skip `docs/CLAUDE.md` — it governs how you work.


<!-- ==================================================================== -->
# FILE: CLAUDE.md
<!-- ==================================================================== -->

# CLAUDE.md — Project Root

Allergen cross-contamination safety layer for a food-prep workstation.
See `docs/product/01-thesis.md` for what this is.

> **Engineering conduct is governed by `docs/CLAUDE.md`** (pre-existing, authoritative:
> think before coding, simplicity first, surgical changes, goal-driven execution). This file
> adds *project* context only and does not restate it.
>
> This root file exists because `docs/CLAUDE.md` is only reliably loaded while working inside
> `docs/`, and its rules must apply to `src/` work too.

## Operating procedure

**Every session, before acting:**
1. `docs/PROJECT_STATE.md` — status, next action, unresolved assumptions
2. `docs/README.md` — the index and the source-of-truth table
3. The architecture doc owning the subsystem you are touching

**Before writing any code:** `docs/architecture/22-interfaces.md` (the only home for
signatures) and `docs/engineering/33-testing-strategy.md`.

**At the end of a session:** update `docs/PROJECT_STATE.md` §2, §3, §5, §8.

## Rules specific to this project

1. **Never let perception import safety.** `state/`, `risk/`, `policy/`, `orders/` may not
   import `perception/`. CI enforces it; do not work around it.
2. **The reasoning core is pure.** No wall clock, no I/O, no randomness in
   `state/`/`risk/`/`policy/`. Time comes from `event.t_occurred`. This is what makes replay
   deterministic — see `ADR-0001`.
3. **Never branch on `confidence`.** Branch on `grade`. See `ADR-0004`.
4. **The system never claims food is safe or contaminated.** It reports what was observed and
   not observed. See `docs/product/02-safety-boundaries.md`.
5. **A bug report is a scenario file.** Reproduce in `/scenarios/`, then fix. The fixture
   becomes a permanent regression test.
6. **Code existing is not "done."** A phase is `VERIFIED` only with the evidence artifact
   named in `docs/engineering/38-workflow.md`.
7. **Build the reasoning core before perception.** P1 needs no camera and is the part that is
   actually novel.

## When docs and code disagree

That is a defect, not a doc edit. Decide which is wrong first. Precedence:
`docs/CLAUDE.md` > ADRs > `docs/product/` > `docs/architecture/` > `docs/engineering/` >
code comments.


<!-- ==================================================================== -->
# FILE: docs/CLAUDE.md
<!-- ==================================================================== -->

# CLAUDE.md

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.


<!-- ==================================================================== -->
# FILE: docs/PROJECT_STATE.md
<!-- ==================================================================== -->

# Project State

**Operational checkpoint.** Authoritative for **status only** — never for design. Update at
the end of every working session and at every phase gate.

**Last updated:** 2026-09-12 · **Phase:** P0 not started · **Mode:** planning complete

---

## 1. Architectural state
Fully specified, not implemented. All layer boundaries, interfaces, and models are defined
in `docs/architecture/`. Twelve ADRs accepted (`docs/decisions/`). No architectural question
is currently open that blocks P0.

## 2. What has been implemented
**Nothing.** The repository contains documentation only. No `src/`, no `tests/`, no
`config/`, no dependencies, no git repository.

## 3. What has been verified
**Nothing.** No code, therefore no evidence artifacts.

| Phase | Status | Evidence |
|---|---|---|
| P0 Foundations | `OPEN` | — |
| P1 Reasoning core | `OPEN` | — |
| P2 Orders & knowledge | `OPEN` | — |
| P3 Worker interface | `OPEN` | — |
| P4 Perception: zones/contact | `OPEN` | — |
| P5 Perception: carriers/resets | `OPEN` | — |
| P6 Demo hardening | `OPEN` | — |

## 4. What remains
All of P0-P6 (`engineering/38-workflow.md`).

## 5. Currently being worked on
Nothing. Planning phase closed; awaiting a decision to begin P0.

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
**Begin P0.** Concretely: initialize git, create the `src/` skeleton with the import-lint
rule, define `domain/` types and event schemas v1, and land `EventLog` with its reorder
window. Do **not** start perception. P1 is the phase that proves the thesis and it needs no
camera.

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


<!-- ==================================================================== -->
# FILE: docs/README.md
<!-- ==================================================================== -->

# Documentation Index

This directory is the authoritative specification of the system. Source code implements
these documents; it does not define them. When code and docs disagree, that is a defect —
see `engineering/38-workflow.md` for how to resolve it.

## Read in this order

**Entering the repo for the first time (agent or human):**

1. `/CLAUDE.md` (repo root) — project context + pointers
2. `docs/CLAUDE.md` — engineering conduct (pre-existing, authoritative, do not edit)
3. `docs/PROJECT_STATE.md` — what is built, verified, and next
4. `docs/product/01-thesis.md` — what we are building and why
5. `docs/product/02-safety-boundaries.md` — what the system may and may not claim
6. `docs/architecture/10-system-overview.md` — the layer architecture
7. Then the specific model doc for the subsystem you are touching

**Before writing any code**, additionally read `engineering/33-testing-strategy.md` and
`engineering/38-workflow.md`.

## Tree

```
docs/
  README.md                        this file
  CLAUDE.md                        engineering conduct (PRE-EXISTING — do not edit)
  PROJECT_STATE.md                 operational handoff checkpoint

  product/
    01-thesis.md                   frozen product thesis
    02-safety-boundaries.md        supported / unsupported claims, fail-safe behavior
    03-scenarios.md                canonical scenarios A-H (drive the test suite)

  architecture/
    10-system-overview.md          layers, dataflow, the event-log boundary
    11-domain-model.md             entities and relationships
    12-event-model.md              event catalog and schemas
    13-state-model.md              carrier state machine, epistemic status
    14-contamination-model.md      taint, propagation, reset semantics
    15-risk-engine.md              pathway search, tiers, outputs
    16-alert-model.md              alert lifecycle, dedup, escalation
    17-order-model.md              tickets, restrictions, binding
    18-allergen-knowledge.md       taxonomy, ingredient map, recipes
    19-temporal-model.md           clocks, ordering, windows, staleness
    20-spatial-model.md            station frame, zones, contact predicate
    21-perception-contract.md      what perception must produce (not how)
    22-interfaces.md               ALL subsystem interface signatures
    23-failure-modes.md            failure taxonomy and containment
    24-privacy-security.md         data lifecycle and threat model
    25-observability.md            evidence trace, logging, inspector

  engineering/
    30-repository-layout.md        source tree and dependency rules
    31-configuration.md            config hierarchy, schema, validation
    32-dependency-policy.md        principles for selecting dependencies
    33-testing-strategy.md         test hierarchy and what each level proves
    34-evaluation-framework.md     metrics and acceptance criteria
    35-data-and-simulation.md      datasets, annotation, synthetic scenarios
    36-replay-and-scenarios.md     scenario file format specification
    37-demo-plan.md                demo architecture and script
    38-workflow.md                 gates, status model, doc maintenance
    39-implementation-plan.md      technology selection, build order, parallelization
    40-team-split.md               three-session ownership, kickoff prompts, merge rhythm protocol

  decisions/
    README.md                      ADR index and the threshold for writing one
    ADR-NNNN-*.md                  individual decision records

  experiments/
    README.md                      experiment protocol and index
```

## Source-of-truth table

Every concept has exactly one authoritative home. Other documents **reference**, never restate.
If you find a definition duplicated, the duplicate is the bug.

| Concept | Authoritative document |
|---|---|
| Engineering conduct, code style discipline | `docs/CLAUDE.md` (pre-existing) |
| What the product is / claims / refuses to claim | `product/01-thesis.md`, `product/02-safety-boundaries.md` |
| Canonical behavioral scenarios (A-H) | `product/03-scenarios.md` |
| Layer boundaries and dataflow | `architecture/10-system-overview.md` |
| Entity definitions (Carrier, Ticket, Taint, ...) | `architecture/11-domain-model.md` |
| Event type catalog and field schemas | `architecture/12-event-model.md` |
| Carrier state machine, epistemic status values | `architecture/13-state-model.md` |
| What "contamination pathway" means; reset validity | `architecture/14-contamination-model.md` |
| Risk levels, pathway algorithm, tier selection | `architecture/15-risk-engine.md` |
| Alert identity, lifecycle, dedup, escalation | `architecture/16-alert-model.md` |
| Ticket lifecycle, restriction normalization, binding | `architecture/17-order-model.md` |
| Allergen taxonomy, ingredient->allergen, recipes | `architecture/18-allergen-knowledge.md` |
| Time semantics, ordering, staleness thresholds | `architecture/19-temporal-model.md` |
| Station coordinate frame, zones, contact predicate | `architecture/20-spatial-model.md` |
| Perception output obligations | `architecture/21-perception-contract.md` |
| **All interface signatures** | `architecture/22-interfaces.md` |
| Failure taxonomy and containment | `architecture/23-failure-modes.md` |
| Data lifecycle, retention, threat model | `architecture/24-privacy-security.md` |
| Evidence trace structure | `architecture/25-observability.md` |
| Worker-facing surfaces and actions | `architecture/26-human-interaction.md` |
| Source tree, module dependency rules | `engineering/30-repository-layout.md` |
| Config keys, defaults, validation | `engineering/31-configuration.md` |
| Test levels and required evidence | `engineering/33-testing-strategy.md` |
| Metrics, targets, acceptance gates | `engineering/34-evaluation-framework.md` |
| Scenario file format | `engineering/36-replay-and-scenarios.md` |
| Demo script and requirements | `engineering/37-demo-plan.md` |
| Technology choices, build order, LOC/time estimates | `engineering/39-implementation-plan.md` |
| Who owns which modules; per-session kickoff prompts | `engineering/40-team-split.md` |
| Phase status, gates, doc maintenance | `engineering/38-workflow.md` + `PROJECT_STATE.md` |
| Why a decision was made | `decisions/ADR-NNNN-*.md` |

**Precedence when documents conflict:** `docs/CLAUDE.md` (conduct) > ADRs (decisions,
most recent wins) > `product/` (thesis) > `architecture/` (design) > `engineering/`
(process) > code comments. `PROJECT_STATE.md` is authoritative **only** for status, never
for design.


<!-- ==================================================================== -->
# FILE: docs/product/01-thesis.md
<!-- ==================================================================== -->

# Product Thesis (FROZEN)

Status: **FROZEN.** Changing this document requires an ADR and invalidates every
downstream architecture document. Do not edit casually.

## One sentence

A prep-station safety layer that maintains a live model of which hands, tools, surfaces,
and shared containers currently carry which allergens, and ensures the allergen reset
protocol actually happens before a restricted order is prepared.

## The flow the engineering system must implement

```
dietary restriction -> ticket -> allergen knowledge -> workstation preparation
  -> observed contact events -> persistent contamination state
  -> risk reasoning -> worker intervention
```

## The core engineering problem

**Representing the state and history of preparation interactions well enough to reason
about potential allergen transfer.** Not ingredient detection. Not object detection. Not
video classification.

The architecture must natively distinguish:

```
pesto -> knife -> bagel -> restricted order          RISK: pathway open
pesto -> knife -> [TOOL_SWAP] -> bagel -> order      NO RISK: pathway broken
pesto -> knife -> [WIPE] -> bagel -> order           RISK: wipe is not a reset (see 14)
pesto -> knife -> [off-camera 40s] -> bagel -> order UNVERIFIED: epistemic degradation
```

All four differ only in what happened *between* two contacts. Therefore time, ordering,
and reset semantics are load-bearing, not incidental.

## Three design commitments (non-negotiable)

**1. Identity comes from configuration; perception supplies only the verb.**
The system does not recognize pesto. It knows from the station map that zone 7 contains
pesto, and observes that a hand entered zone 7. This converts an open-set recognition
problem into a closed-set geometric one. See `architecture/20-spatial-model.md`.

**2. Contamination is a property of carriers, not of dishes.**
Taint attaches to gloves, tools, surfaces, and containers. Tickets never hold taint; they
supply only a restriction filter, a time window, and an expected zone set. This is why
concurrent orders require no attribution logic. See `architecture/14-contamination-model.md`.

**3. The system reports observation, never contamination.**
It may assert "I did not observe a glove change between the pesto contact and this ticket."
It may never assert "this food is contaminated" or "this food is safe." The first is
falsifiable and resolvable by a human in one tap. The second is unverifiable in principle.
See `product/02-safety-boundaries.md`.

## The intervention model

Uncertainty is routed to the **cheapest** action, not the loudest one.

*Intent and cost model below; `architecture/15-risk-engine.md` is authoritative for the
selection rules themselves.*

| Tier | Fires | Cost to comply | Evidence required |
|---|---|---|---|
| **0 Reset Prompt** | At ticket bind, before prep | ~8 seconds | **None.** Any uncertainty. Never has to be right. |
| **1 Interrupt** | Mid-prep | One component / tool swap | `OBSERVED`-grade pathway only |
| **2 Hold at pass** | Item complete | Full remake + delay | Observed pathway, no reset, unresolved by human |
| **3 —** | never | — | System never declares food safe, releases its own hold, or contacts a customer |

Tier 0 absorbs essentially all uncertainty at near-zero operational cost. Tiers 1 and 2,
which carry real false-positive cost, are gated behind observed contact. This asymmetry is
the load-bearing wall of the whole design.

## The signature capability

Back-contamination of shared containers. A worker handles pesto, then without changing
gloves reaches into the shared mayonnaise tub. The tub is now a pine-nut carrier for every
subsequent ticket. No POS knows this. No human tracks it. It is directly observable and it
is what the architecture exists to represent.

## Explicit non-goals

- Recognizing arbitrary foods or ingredients from pixels
- Verifying cleaning efficacy
- Identifying individual workers or customers
- Replacing staff training, labeling, or existing allergy protocols
- Monitoring anything beyond one configured prep station
- Any customer-facing "verified safe" signal


<!-- ==================================================================== -->
# FILE: docs/product/02-safety-boundaries.md
<!-- ==================================================================== -->

# Safety Boundaries

These are **behavioral requirements encoded in the system**, not disclaimers. Each is
traceable to an architectural mechanism and a test.

## Supported claims

The system may state, and the architecture must be able to substantiate:

| Claim | Mechanism | Test level |
|---|---|---|
| "A hand entered the pesto zone at T" | Contact event, `OBSERVED` grade | perception + replay |
| "No glove change was observed between T1 and T2" | Absence of `RESET` event in window | replay |
| "This tool has an unbroken contact path from an allergen source" | Pathway search (`15`) | risk-engine |
| "This station's state is not currently verifiable" | Epistemic status `UNKNOWN`/`STALE` (`13`) | replay |
| "This ticket's restriction could not be resolved" | `Restriction.resolution = AMBIGUOUS` (`17`) | order-model |

## Unsupported claims — architecturally prohibited

The system must be **structurally incapable** of producing these, not merely discouraged:

| Prohibited claim | Enforcement |
|---|---|
| "This food is allergen-free / safe" | No `SAFE` value exists in any risk enum. `RiskLevel` has no positive-safety member. |
| "Contamination occurred" | `RiskLevel` names *pathway* states, never physical outcomes. UI copy lint forbids the word in alert templates. |
| "This surface is clean because it was wiped" | `SURFACE_WIPE` is recorded but is not in the valid-reset set (`14`). Unit-tested. |
| "Cleaning was effective" | Wash-cycle resets carry grade `ASSERTED`, never `OBSERVED`. |
| Any statement about a named worker | No identity fields exist on the worker entity (`11`, `24`). |

## Human responsibility

The human is the decision-maker at every tier. The system:

- **proposes** remediation; it never performs one
- **holds** an item; it never releases one — only a human clears a Tier 2 hold
- **records** a human assertion as `ASSERTED` grade and never silently promotes it to `OBSERVED`
- **cannot** cancel, refund, or communicate with a customer

## Fail-safe behavior

The governing rule: **degraded perception must increase conservatism and decrease cost, never the reverse.**

| Condition | Behavior |
|---|---|
| Carrier not observed recently | Epistemic status degrades -> pessimistic closure -> Tier 0 at next bind |
| Camera fault / total vision loss | Station enters `PROTOCOL_ONLY` mode: Tier 0 still fires on every restricted ticket, UI states vision is unavailable. **The product retains its primary value with zero perception.** |
| Tracker identity ambiguity | Confusable carriers' taint sets are **merged** (pessimistic), both marked `STALE`. Never silently reassigned. |
| Reasoning core exception | Station enters `PROTOCOL_ONLY`, existing Tier 2 holds persist, incident logged. Never fail-open to silence. |
| Ticket restriction ambiguous | Binding is **blocked**. The system asks; it does not guess. |

## The one rule that subsumes the rest

> Low confidence must trigger a **human-verification workflow at the cheapest tier**, never a
> lowered alert threshold at a high tier.

Lowering thresholds under uncertainty makes the system noisiest exactly when it is least
trustworthy, which is the mechanism by which safety systems get ignored. See
`decisions/ADR-0005`.


<!-- ==================================================================== -->
# FILE: docs/engineering/40-team-split.md
<!-- ==================================================================== -->

# Team Split: Three Sessions

How three people with three Claude Code sessions work this repo without colliding.
Companion to `38-workflow.md` (phases and gates) and `39-implementation-plan.md` (stack).

---

## The shape of it

**P0 is a serialization point. Everything after it is genuinely parallel.**

Until the event schemas and domain types exist, two of three sessions would be writing
against types that do not exist — and would each invent a different `Event`. Three
plausible, incompatible interpretations is the most expensive failure available here,
because it surfaces at integration when there is no time left to fix it.

```
hour 0 ─────────── 2 ──────────────────────────────── 13 ────────── 18
  │                │                                    │            │
  │  ONE session   │        THREE sessions              │  converge  │
  │  owns P0       │        against frozen contracts    │            │
  │                │                                    │            │
  └─ others do work that needs no code ─┘
```

## Ownership — by module, never by task

Two people must never edit the same file. The layer boundaries in `30-repository-layout.md`
already draw the lines; use them as territory.

| | Owns | Also owns | Never touches |
|---|---|---|---|
| **1 · Core** | `domain/ events/ state/ risk/ policy/ orders/ knowledge/ replay/` | `scenarios/`, `config/knowledge/` | `perception/ ui/` |
| **2 · Perception** | `perception/ scripts/` | physical station, `config/station/`, recordings, annotations | `state/ risk/ policy/ ui/` |
| **3 · Interface** | `ui/ runtime/` | demo script, rehearsal, pitch | `state/ risk/ policy/ perception/` |

**One shared file needs a lock: `docs/architecture/22-interfaces.md`.** It is the contract
all three build against. Nobody edits it alone — a change there is a 60-second conversation
first, then one person edits.

## Hours 0-2: the part people get wrong

Sessions 2 and 3 are **not blocked** during P0. They have real work that touches no code:

- **Person 2** — build the physical station. Mount the camera, tape the corner markers,
  print and attach ArUco tags, place and label bins, record the 12 video fixtures and the
  30 minutes of normal prep (`35-data-and-simulation.md`). This is a full two hours and it
  is on the critical path for P4.
- **Person 3** — build the station display against mocked data. Start from the published
  demo-screen artifact; it is already the correct layout, colour semantics, and beat
  sequence. Swapping mocked state for real state later is a small change.

Both are genuinely useful and neither can break anything.

## Integration rhythm

Merge to `main` and run the full suite **every three hours.** Not at the end.

> **Tripwire:** if a merge takes more than 15 minutes to resolve, the split is failing.
> Collapse to two streams immediately. Do not push through it.

## Prerequisite — blocking

Three parallel sessions without version control is not a plan. Run this first:

```
git init
printf '.DS_Store\ndata/\n__pycache__/\n*.pyc\n.venv/\n' > .gitignore
git add -A && git commit -m "Architecture and implementation plan"
git branch core perception interface
```

---

## Kickoff prompts

Copy-paste. Each is self-contained: reading list, ownership, gate, non-goals.

### Session 1 — Core

```
You are building the reasoning core of this project. Read, in order:
docs/PROJECT_STATE.md, docs/README.md, docs/product/01-thesis.md,
docs/product/02-safety-boundaries.md, docs/product/03-scenarios.md,
docs/architecture/10-system-overview.md, 11-domain-model.md, 12-event-model.md,
13-state-model.md, 14-contamination-model.md, 15-risk-engine.md, 16-alert-model.md,
22-interfaces.md, docs/engineering/33-testing-strategy.md, 36-replay-and-scenarios.md,
38-workflow.md, 39-implementation-plan.md.

Work on branch `core`. You own: domain/ events/ state/ risk/ policy/ orders/
knowledge/ replay/ scenarios/ config/knowledge/. You may not create or edit
perception/ or ui/. You may not edit docs/architecture/22-interfaces.md without
stopping and telling me first — two other people are building against it.

Build P0 then P1 as defined in docs/engineering/38-workflow.md.

P0 gate: every event type round-trips; import-linter rejects a deliberately planted
violation; config validation rejects a deliberately malformed bundle; the clock lint
rejects a planted now() call in state/.

P1 gate: all 13 scenario fixtures in docs/product/03-scenarios.md pass as replay tests,
property tests green, each fixture byte-identical across two runs, zero silent misses.
Write the fixtures as you build — they are the specification, not an afterthought.

Do not start perception. Do not build a UI beyond whatever CLI output you need.
Stop and report at each gate rather than continuing past it.
```

### Session 2 — Perception

```
You are building the perception layer of this project. Read, in order:
docs/PROJECT_STATE.md, docs/README.md, docs/product/01-thesis.md,
docs/architecture/10-system-overview.md, 12-event-model.md, 19-temporal-model.md,
20-spatial-model.md, 21-perception-contract.md, 22-interfaces.md, 23-failure-modes.md,
docs/engineering/35-data-and-simulation.md, 39-implementation-plan.md.

Work on branch `perception`. You own: perception/ scripts/ config/station/ data/.
You may not import from state/, risk/, policy/, orders/, or ui/ — CI enforces this and
working around it is the one unforgivable change in this repo. You may not edit
docs/architecture/22-interfaces.md without stopping and telling me first.

First two hours, no code: build the physical station, calibrate, and record the 12
annotated video fixtures plus 30 minutes of normal hazard-free prep, per
docs/engineering/35-data-and-simulation.md. Annotate at the EVENT level, and annotate
occlusion intervals even though it is tedious — that is ground truth for the metric
that matters most.

Then build P4 (calibration, zones, HSV glove tracking, contact episodes with dwell and
hysteresis, occlusion to epistemic events) and P5 (ArUco tool identity, swaps, glove
change) per docs/engineering/38-workflow.md and 39-implementation-plan.md.

P4 gate: event-level precision/recall on the 12 clips meets targets, occlusion-reporting
recall >= 0.95, under 1 nuisance alert per hour on the normal-prep set.

Your hardest obligation is honesty, not accuracy: failing to report that a carrier became
unobservable is a more serious defect than a false detection. Read
docs/architecture/21-perception-contract.md twice on this point.
```

### Session 3 — Interface

```
You are building the interface and runtime of this project. Read, in order:
docs/PROJECT_STATE.md, docs/README.md, docs/product/01-thesis.md,
docs/product/02-safety-boundaries.md, docs/architecture/10-system-overview.md,
16-alert-model.md, 22-interfaces.md, 25-observability.md, 26-human-interaction.md,
docs/engineering/37-demo-plan.md, 39-implementation-plan.md.

Work on branch `interface`. You own: ui/ runtime/. You may not edit state/, risk/,
policy/, or perception/. You may not edit docs/architecture/22-interfaces.md without
stopping and telling me first.

First two hours: build the station display against mocked state. The published demo-screen
artifact is the approved layout, colour semantics, and beat sequence — match it. Four
panes in dataflow order; worker surface at the bottom; no green state anywhere, because
green reads as a safety claim the system is forbidden from making.

Then build P3: the three worker surfaces (Tier 0 checklist, Tier 1 interrupt, Tier 2 hold),
worker actions emitted as OPERATOR_ASSERTION events into the log, evidence-trace rendering,
live carrier grid, and PROTOCOL_ONLY mode complete.

P3 gate: every alert type resolvable in <= 2 taps, measured on a teammate rather than
yourself; alert-copy lint green; and a complete demo runs end to end in PROTOCOL_ONLY
with no camera attached.

That last one is the real target. When it passes, the team has a shippable product
regardless of how perception goes.
```

## When not to do this

If two of the three are not comfortable driving Claude Code, **do not force a three-way
split.** One strong driver on the core plus two people on station build, recordings,
scenario authoring, demo rehearsal and the pitch is a legitimate allocation and will beat a
messy parallel attempt. The coordination tax is real and it is paid in the last three hours,
which are the ones you cannot afford to lose.


<!-- ==================================================================== -->
# FILE: docs/product/03-scenarios.md
<!-- ==================================================================== -->

# Canonical Scenarios (A-H)

These eight scenarios are the **behavioral contract** of the system. Each has a
corresponding executable replay fixture in `/scenarios/`, and each is a required gate for
Phase P1 (see `engineering/38-workflow.md`).

This document is the source of truth for *what each scenario means*.
`engineering/36-replay-and-scenarios.md` is the source of truth for the *file format*.
The `/scenarios/*.yaml` files are the source of truth for the *exact event sequences*.

Station used throughout: bins `pesto`, `mayo`, `turkey`, `bread`; carriers `gloves`,
`spreader`, `board`, `landing`. Restriction throughout: `PINE_NUT`.

---

## A — No risk

Ticket has no restriction, or a restriction with no intersection against the station map.

**Expected:** complete silence. No Tier 0. No alert. Carrier state updates normally.
**Proves:** the system is quiet by default. *A scenario that asserts the absence of output is
as important as one that asserts presence.*

## B — Direct risk, prevented

Gloves and spreader carry `OBSERVED` taint `{PINE_NUT}` from a prior ticket. A `PINE_NUT`
ticket binds.

**Expected:** Tier 0 fires **at bind, before any motion**, listing exactly the carriers
requiring reset. On observing `GLOVE_CHANGE` + `TOOL_SWAP`, carriers reset to
`OBSERVED`-clean, prompt clears, prep proceeds silently.
**Proves:** the primary value path — contamination is *prevented*, not merely detected.

## C — Indirect risk (multi-hop)

`gloves -> pesto`, then `gloves -> board`, then clean bread placed on `board`, then bread
enters the restricted item. No reset anywhere.

**Expected:** pathway of length 3 found; Tier 1 during prep, escalating to Tier 2 if the
item completes unresolved.
**Proves:** transitive propagation through surfaces; the pathway search is not a
first-order adjacency check.

## D — False positive (worker actually cleaned)

System believes `spreader` is tainted; the swap happened off-camera.

**Expected:** prompt reads *"Spreader last observed contacting pesto. Replacement not
observed."* Worker taps **"Already swapped"** -> `OPERATOR_ASSERTION` event -> carrier
becomes `ASSERTED`-clean -> prompt clears. One tap. No remake. No argument.
**Proves:** the epistemic framing converts what would be a dispute into a one-tap
resolution, and human corrections are first-class events in the same log.

## E — False negative (unobserved transfer)

A real transfer occurs entirely outside the contact model (e.g. a splash, an unmodeled
carrier).

**Expected:** the system produces **no** Tier 1/2 alert — and this is not scored as a
silent failure *provided* the relevant carriers were reported `STALE`/`UNKNOWN` and Tier 0
fired at bind. A **Silent Miss** is only recorded when the system asserted `TRACKED`-clean
and was wrong.
**Proves:** declining to claim is architecturally distinct from missing. See
`engineering/34-evaluation-framework.md`.

## F — Concurrent restricted orders

Two tickets with different restrictions bound to one station simultaneously.

**Expected:** no per-ticket attribution is attempted. Station raises condition
`MULTI_RESTRICTION` -> Tier 0 escalation: *"Two active restrictions — sequence them."*
**Proves:** carrier-held taint makes concurrency a non-problem, and the system enforces
existing kitchen protocol rather than inventing one it cannot support.

## G — Ambiguous restriction

Ticket free-text reads `"ALLERGY"` with no allergen named.

**Expected:** `Restriction.resolution = AMBIGUOUS`. **Binding is blocked.** A resolution
request is routed to front-of-house. No prep may start. The system never guesses.
**Proves:** bad input is surfaced *before* food is made, not after.

## H — Out of view

Hands leave the station frame for longer than `t_stale_gloves`.

**Expected:** `gloves` epistemic status -> `UNKNOWN` -> pessimistic closure -> Tier 0 at
next restricted bind: *"Hands left the station. New gloves before starting."*
**Proves:** occlusion is an *input* to the design, not a failure of it — it degrades into
an 8-second action.

---

## Derived scenarios (also fixtures, lower priority)

| Id | Description | Proves |
|---|---|---|
| **I** | Back-contamination: `pesto -> gloves -> mayo tub`; later ticket uses mayo | The signature capability. **Required for demo.** |
| **J** | Wipe is not a reset: `pesto -> board`, `SURFACE_WIPE`, restricted item on board | `WIPE` does not clear taint |
| **K** | Tracker identity switch between two tools | Taint sets merge pessimistically |
| **L** | Camera fault mid-ticket | Clean transition to `PROTOCOL_ONLY`; existing holds persist |
| **M** | Alert storm suppression: 10s of continuous contact with one tainted tool | Exactly one alert, not forty |


<!-- ==================================================================== -->
# FILE: docs/architecture/10-system-overview.md
<!-- ==================================================================== -->

# System Overview

## The one architectural idea

**The Observation Log is the spine. Everything downstream of it is a pure, deterministic
fold.**

```
                    PROBABILISTIC                 |            DETERMINISTIC
                                                  |
 Frames -> Detection -> Tracking -> Assembly  ==>  OBSERVATION LOG  ==>  Reduce -> Risk -> Policy -> UI
 (ephemeral)                                      |   (append-only,
                                                  |    versioned,
                                                  |    serializable)
```

Formally:

```
WorldState(t) = fold(reduce, ObservationLog[0..t], InitialState, Config)
RiskAssessment = f(WorldState, ActiveTickets, Knowledge, Config)     -- pure
Interventions  = g(RiskAssessment, AlertState, Config)               -- pure
```

Consequences that fall out **by construction** rather than by discipline:

- Deterministic replay is guaranteed, not aspirational
- The safety core is fully testable with zero camera hardware
- The evidence trace is free: every state mutation carries the event id that caused it
- Perception and reasoning can be built in parallel by different people
- The demo can be driven from a recorded log if live perception degrades

This is `decisions/ADR-0001`. Nearly every other decision serves it.

## Layers

| # | Layer | Responsibility | Produces | May depend on |
|---|---|---|---|---|
| 1 | **Sensing** | Physical station -> frames + timestamps | `Frame` (ephemeral, never persisted) | — |
| 2 | **Perception** | Frame -> detections in station coordinates | `Detection` (confidence-bearing) | sensing |
| 3 | **Tracking** | Detections -> stable entity identities over time | `Track` | perception |
| 4 | **Assembly** | Tracks -> discrete semantic events, with dwell/hysteresis/debounce | **`Event`** | tracking, `domain` |
| 5 | **Log** | Ordering, reorder window, commit, persistence | committed `Event` stream | `domain` |
| 6 | **State** | `(State, Event) -> State`. Carrier taint + epistemic status | `WorldState` | log, `domain` |
| 7 | **Knowledge** | Allergen taxonomy, ingredient map, recipes | resolution queries | config |
| 8 | **Orders** | Ticket intake, restriction normalization, binding lifecycle | `Ticket` | knowledge, `domain` |
| 9 | **Risk** | Pathway search over the temporal contact graph | `RiskAssessment` | state, knowledge, orders |
| 10 | **Policy** | Tier selection, alert identity, lifecycle, suppression | `Intervention` | risk |
| 11 | **Presentation** | Worker display, assertion capture, inspector | UI + `OPERATOR_ASSERTION` events | policy |
| 12 | **Observability** | Evidence trace, structured logs, replay export | traces | all (read-only) |

## The mandatory boundary

> **Layers 6-11 may not import layers 1-4. The only thing that crosses is a committed `Event`.**

Enforced mechanically by an import-lint rule in CI (`engineering/30-repository-layout.md`),
not by convention. A perception change must never be able to alter a safety decision except
by changing which events it emits.

This is what makes it possible for the system to say *"perception believes the pesto
container was handled, confidence 0.87"* without that sentence being able to reach the
conclusion *"the customer's food is contaminated."* Confidence is thresholded into an
`EvidenceGrade` at layer 4 and never reappears as a float in layers 6-11 (`ADR-0004`).

## Feedback edges (the only ones permitted)

1. **Worker assertion** — layer 11 emits `OPERATOR_ASSERTION` into layer 5. Human
   corrections are ordinary events, replayable and auditable. Not a side channel.
2. **Mode change** — layer 12 health monitoring emits `STATION_MODE_CHANGED` into layer 5
   (e.g. entering `PROTOCOL_ONLY`). Mode is state, so it must be an event.

No other backward edge exists. There is no path by which risk output influences perception.

## Runtime modes

| Mode | Trigger | Behavior |
|---|---|---|
| `FULL` | Normal | All tiers active |
| `PROTOCOL_ONLY` | Vision unavailable / reasoning fault | All carriers `UNKNOWN`; Tier 0 on every restricted bind; Tier 1 disabled; existing Tier 2 holds persist; UI states vision is down |
| `REPLAY` | Scenario or recorded log | Layers 1-4 replaced by a log reader; layers 5-12 byte-identical |
| `CALIBRATION` | Setup | Zone authoring; no tickets may bind |

`PROTOCOL_ONLY` is a **supported product mode, not an error path.** It delivers the
majority of the safety value with no perception at all, which is both the honest assessment
of where value sits and the demo's safety net.


<!-- ==================================================================== -->
# FILE: docs/architecture/16-alert-model.md
<!-- ==================================================================== -->

# Alert Model

## Alert identity — the anti-spam mechanism

```
pathway_signature = hash(ticket_id, allergen_id, root_source_carrier, ordered_node_ids)
alert_key         = (station_id, pathway_signature)
```

Two observations are **the same alert** iff they share an `alert_key`. Ten seconds of
continuous contact with one tainted spreader yields one pathway, one signature, one alert —
updated, not re-raised.

Suppression happens at **three** layers, each solving a different duplication:

| Layer | Mechanism | Solves |
|---|---|---|
| Assembly (`12`) | Contact **episodes** (`BEGIN`..`END`) with dwell + hysteresis | 30fps -> 1 event |
| Policy (this doc) | `alert_key` dedup | Same hazard re-derived on each tick |
| Presentation (`H`) | One visible alert per station, highest tier wins | Visual overload |

Solving it only at the UI layer would leave the log full of noise and poison the evaluation
metrics; solving it only at assembly would still re-raise on every reassessment. All three
are required.

## Lifecycle

```
RAISED ──ack──> ACKNOWLEDGED ──┐
   │                            ├──> RESOLVED_BY_RESET      (a valid reset broke every pathway)
   │                            ├──> RESOLVED_BY_ASSERTION  (human vouched; ASSERTED grade)
   ├──escalate──> ESCALATED ────┤
   │                            └──> RESOLVED_BY_REMAKE     (item voided / reworked)
   └──expire──> EXPIRED         (Tier 0 only, on ticket void)
```

Rules:

- **Tier 2 has no expiry and no auto-resolution.** Only an explicit human action clears a
  hold. The system never releases its own hold (`product/02`).
- Tier 0 auto-resolves the instant its preconditions are met — the checklist items tick
  themselves off as resets are observed. This is deliberate: compliance should feel like
  progress, not paperwork.
- Tier 1 auto-resolves on a pathway-breaking reset, and the UI *shows* the resolution rather
  than silently clearing it, so the worker learns the causal link.

## Escalation

| From | Condition | To |
|---|---|---|
| Tier 0 | Ticket reaches `IN_PREP` with preconditions still unmet | Tier 1 |
| Tier 1 | Unacknowledged for `t_escalate` (default 20s) **and** ticket reaches `COMPLETE` | Tier 2 |
| Tier 2 | Unresolved for `t_manager` (default 60s) | Manager surface (deferred post-MVP) |

Escalation is time-and-lifecycle driven, never severity-inflation driven. An alert never
escalates merely because it has been repeated.

## Cooldown

After `RESOLVED_BY_ASSERTION`, the same `alert_key` is suppressed for `t_cooldown`
(default 120s) to prevent immediately re-alerting on the same human-vouched carrier. The
suppression is **logged as a suppression event** so evaluation can distinguish "did not
fire" from "fired and was suppressed" — without that distinction the nuisance-rate metric is
meaningless.

## Alert payload

```
Alert
  alert_id, alert_key, pathway_signature
  tier: 0 | 1 | 2
  ticket_id, allergen_id
  headline        : str         # <= 6 words, read at a glance
  required_actions: List<Action># e.g. [NEW_GLOVES, SWAP_TOOL(spreader)]
  derivation      : List<(event_id, rule_id, state_delta)>   # the evidence trace
  raised_at, state, acknowledged_by_slot?
```

`headline` and `required_actions` are what the worker sees. `derivation` is what a manager
or engineer inspects. Both come from the same object, so they cannot disagree — a UI copy
lint test asserts `headline` never contains a prohibited claim word (`02`).


<!-- ==================================================================== -->
# FILE: docs/architecture/17-order-model.md
<!-- ==================================================================== -->

# Order / Ticket Model

## Abstract source

No third-party platform appears anywhere in the core. The boundary is:

```
OrderSource (interface, see `22`)
  poll() -> List<RawOrder>
  RawOrder: { external_id, items: List<str>, notes: List<str>, received_at }
```

MVP implementations: `ManualEntrySource` (a cashier types it) and `FixtureSource` (replay).
Any POS/delivery adapter is an implementation of this interface and lives in an adapter
module, never in `orders/` core. Delivery-platform integration is explicitly **deferred**
(`engineering/38-workflow.md` priorities) — free-text allergy notes are a normalization
problem, not an integration problem, and the normalizer is where the value is.

## Restriction normalization

```
normalize : (raw_text, Knowledge) -> Restriction
```

Three outcomes, and the third is the important one:

| Outcome | Condition | Effect |
|---|---|---|
| `RESOLVED` | Text maps to >=1 known allergen with high confidence | `allergen_ids` populated; ticket may bind |
| `AMBIGUOUS` | Allergy intent detected, specific allergen not determinable ("ALLERGY", "no nuts?") | **Binding blocked.** Resolution request routed to front-of-house. |
| `UNRESOLVABLE` | Names something outside the knowledge base | Binding blocked; escalated to a manager |

**The normalizer may never guess.** Low confidence produces `AMBIGUOUS`, never a
best-effort allergen. Enforced by a test asserting that below-threshold inputs never yield
`RESOLVED` (scenario G).

Normalization output is **cached on the ticket**, not recomputed, so that a re-run of the
normalizer (a model change) cannot silently alter an in-flight ticket's meaning.

## Ticket lifecycle

```
RECEIVED ──normalize──┬─ RESOLVED ──> (bindable)
                      └─ AMBIGUOUS/UNRESOLVABLE ──> BLOCKED ──resolve──> RECEIVED
(bindable) ──tap──> BOUND ──> IN_PREP ──> COMPLETE ──┬──> RELEASED
                                                      └──> HELD ──human──> RELEASED | VOIDED
any ──> VOIDED (timeout `t_abandon` = 15m, or explicit)
VOIDED/RELEASED ──rework──> new Ticket{rework_of: id}
```

Invariants (tested):
1. `BLOCKED` -> `BOUND` is unreachable.
2. `HELD` -> `RELEASED` requires an operator event; no timer, no system path.
3. A `VOIDED` ticket contributes no risk assessments but its events remain in the log.

## Binding — explicit, never inferred

`TICKET_BOUND` is produced by a **human action** (one tap on the station display), never by
vision. Inferring which ticket a cook is currently preparing from pixels is not reliably
solvable and every downstream guarantee would inherit its error rate.

This is a deliberate trade of one second of human effort for the removal of an entire class
of unbounded failure (`ADR-0006`). It is not a shortcut, and the doc says so because it will
otherwise be "fixed" by a future contributor.

## Concurrency

The station holds a **set** of bound tickets. Because taint lives on carriers and never on
tickets (`11`), no contact attribution is required and concurrency needs no special
handling in the state or risk layers.

The one concurrency rule that does exist is a protocol rule, not a technical one:

> `>= 2` bound tickets with non-empty restrictions raises station condition
> `MULTI_RESTRICTION` -> Tier 0 escalation: *"Two active restrictions — sequence them."*

This mirrors standard kitchen allergen protocol (prep restricted orders separately). The
system enforces the existing rule rather than inventing one it cannot substantiate
(scenario F).

## Substitutions and rework

A substitution changes `items`, therefore `required_zones`, therefore Tier 0 preconditions.
It emits `TICKET_ITEM_SUBSTITUTED` and triggers reassessment. A rework opens a **new**
ticket referencing the original; state is never mutated backwards, preserving log
append-only semantics.


<!-- ==================================================================== -->
# FILE: docs/architecture/22-interfaces.md
<!-- ==================================================================== -->

# Interface Registry

**Source of truth for every subsystem signature.** Other documents describe semantics and
reference these names; they never restate signatures. If a signature appears elsewhere, the
copy is the defect.

Language-neutral notation. `?` = optional. `!` = raises.

---

## `EventLog`

```
append(e: Event) -> Seq            ! SchemaError, ClockError
read(from: Seq, to: Seq?) -> Iterator<Event>
subscribe(handler) -> Subscription
snapshot_at(seq: Seq) -> WorldState?
```
- **Invariants:** append-only; `seq` gapless and monotonic; events immutable after commit;
  reorder only within `t_reorder`.
- **Errors:** schema violation rejects the event and emits `HEALTH_DEGRADED`; it never
  crashes the runtime.
- **Owner:** `events/`  **Testability:** fully in-memory; no I/O required.

## `EventSink`

```
emit(e: DraftEvent) -> None        ! never raises into the caller
```
- The **write side of the boundary**. The only handle perception and the UI are given.
- A `DraftEvent` lacks `seq` and `t_committed`; the log assigns them at `append`.
- **Invariant:** a rejected or malformed event is quarantined and surfaced via
  `HEALTH_DEGRADED`; it must never propagate an exception back into perception or the UI
  (`23` P10).
- **Owner:** `events/`

## `Reducer`

```
reduce(state: WorldState, e: GradedEvent, cfg: Config) -> (WorldState, List<StateDelta>)
initial(cfg: Config, station: StationConfig) -> WorldState
```
- **Purity:** total, deterministic, no I/O, no clock, no randomness.
- **Note:** `GradedEvent` is a projection of `Event` that **omits `confidence`** — the type
  system is what enforces `ADR-0004`, not reviewer vigilance.
- **Owner:** `state/`

## `RiskEngine`

```
assess(state: WorldState, tickets: List<Ticket>, k: Knowledge, cfg: Config)
    -> List<RiskAssessment>
find_pathways(state, target: CarrierId, allergens: Set<AllergenId>, cfg)
    -> List<Pathway>
check_preconditions(state, ticket: Ticket, k: Knowledge, cfg)
    -> List<CarrierId>            # carriers requiring reset; empty = preconditions met
```
- Pure. No perception types in the signature — this is the mandated separation made
  mechanical.
- **Owner:** `risk/`

## `InterventionPolicy`

```
evaluate(assessments: List<RiskAssessment>, alerts: AlertState, cfg)
    -> List<AlertCommand>          # RAISE | UPDATE | RESOLVE | ESCALATE | SUPPRESS
```
- Pure. Owns tier selection, dedup by `alert_key`, cooldown, escalation timing.
- **Owner:** `policy/`

## `AlertState`

```
open() -> List<Alert>
by_key(alert_key) -> Alert?
cooldowns() -> Map<AlertKey, Timestamp>
apply(cmd: AlertCommand) -> Alert
```
- Policy-owned, derived entirely from the log; recomputable by replay like any other state.
- **Owner:** `policy/`

## `RuntimeController`

```
mode() -> Mode
request_mode(m: Mode, cause: str) -> None     # emits STATION_MODE_CHANGED
health() -> HealthStatus
```
- The **only** owner of mode transitions (`10`). Perception reports health; it does not
  decide mode. Prevents two subsystems racing to set `PROTOCOL_ONLY`.
- **Owner:** `runtime/`

## `OrderSource`

```
poll() -> List<RawOrder>
ack(external_id) -> None
```
- **Implementations:** `ManualEntrySource`, `FixtureSource`. Adapters live in
  `orders/adapters/` and are the only place a third-party schema may appear.

## `RestrictionNormalizer`

```
normalize(raw_text: str, k: Knowledge) -> Restriction
```
- **Invariant:** must return `AMBIGUOUS` rather than a low-confidence `RESOLVED`. Tested.
- **Owner:** `orders/`

## `KnowledgeProvider`

```
allergens_for(ingredient_id) -> (contains: Set, may_contain: Set)
closure(allergen_id) -> Set<AllergenId>
zones_for(item_id) -> List<ZoneId>
resolve_alias(text) -> IngredientId?
version() -> KnowledgeVersion
```
- **Implementation:** versioned file bundle per restaurant. Read-only at runtime.
- **Owner:** `knowledge/`

## `PerceptionPipeline`

```
start(cfg, station: StationConfig, sink: EventSink) -> Handle
stop(h: Handle) -> None
health() -> HealthStatus
```
- Writes **only** to `EventSink`. May import `domain/` and `events/` and nothing else.
- **Owner:** `perception/`

## `Clock`

```
now() -> Timestamp
```
- Injected. `SystemClock` in `FULL`; `LogClock` in `REPLAY`. Direct clock access outside
  `runtime/` fails lint (`19`).

## `ReplayRunner`

```
run(scenario: ScenarioFile) -> ReplayResult
ReplayResult { final_state, alerts: List<Alert>, traces, assertions: List<AssertionResult> }
```
- **Invariant:** byte-identical output across runs for the same scenario + config +
  knowledge version. Asserted by a test that runs each fixture twice and diffs.
- **Owner:** `replay/`

## `WorkerDisplay`

```
render(interventions: List<Alert>, state_summary: StationSummary) -> None
on_action(cb: (WorkerAction) -> None)      # emits OPERATOR_ASSERTION into the log
```
- **Invariant:** worker actions enter the system **only** as events; the UI never mutates
  `WorldState` directly.

---

## Dependency direction (must form a DAG)

```
domain  <- events  <- state  <- risk  <- policy  <- ui
   ^         ^                    ^
   |         |                    |
knowledge ---+              orders +
   ^                               ^
   +------- config ----------------+

perception -> events, domain           (ONLY)
replay     -> events, state, risk, policy
runtime    -> everything (composition root; the only layer permitted to)
```

Verified by an import-lint rule in CI. A violation is a build failure, not a review comment.


<!-- ==================================================================== -->
# FILE: docs/architecture/25-observability.md
<!-- ==================================================================== -->

# Observability

"Alert triggered" is not a debuggable system. The requirement is that we can always answer
**"what did the system believe, and why."**

## The evidence trace

One structure serves four purposes — debugging, evaluation, the worker/manager explanation,
and safety analysis. Because it is the *same* object that drove the decision, the
explanation cannot drift from the behavior.

```
Trace {
  alert_id, pathway_signature,
  steps: List<TraceStep>
}
TraceStep {
  event_id, t_occurred, rule_id,
  state_delta,             # exactly what changed in WorldState
  grade, narrative         # generated from a template table, not free text
}
```

Rendered form (this is literally what a manager sees on a Tier 2 hold):

```
14:31:52  ZONE_ENTRY      gloves -> bin:pesto            OBSERVED   +taint{PINE_NUT} on gloves
14:31:58  CONTACT_BEGIN   gloves <-> tool:spreader       OBSERVED   +taint{PINE_NUT} on spreader (hop 1)
14:32:19  CONTACT_BEGIN   gloves <-> bin:mayo            OBSERVED   +taint{PINE_NUT} on bin:mayo (hop 1)
          -- no GLOVE_CHANGE observed in window --
14:35:03  TICKET_BOUND    #48 restriction PINE_NUT
14:35:03  RULE precondition_unmet  -> blocking: [gloves, tool:spreader, bin:mayo]
14:35:03  ALERT tier=0    "Station not clean for PINE_NUT"
```

The absence line (`-- no GLOVE_CHANGE observed --`) is as important as the presence lines;
it is the system's actual claim (`product/01-thesis.md`).

## Log levels and their consumers

| Stream | Contents | Consumer | Retention |
|---|---|---|---|
| Event log | All committed events | Replay, evaluation, audit | audit window |
| Trace store | Derivations per alert | Manager UI, debugging | audit window |
| Metrics | Counters/histograms: event rates, late rate, occlusion duration, assertion rate, alert rate by tier, **Tier 0 compliance rate**, **pessimistic-closure rate**, reducer latency | Dev + tuning | session |
| Health | Mode changes, degradations, rejected events | Ops + demo safety | session |
| Quarantine | Schema-invalid events | Offline diagnosis | session |

**Prohibited from every stream:** image data, worker identity, customer identity.

## Inspector

A development/manager surface (separate from the worker display) showing: live carrier
states on both axes, active zones and recent contacts, bound tickets and restrictions,
active alerts with traces, mode and health, and a scrubbable event timeline.

The inspector is **read-only** and reads the same projections the runtime uses. It never
has a privileged view — if the inspector can show it, the trace can explain it.

## Replay-driven debugging

Because reasoning is a pure fold (`10`), any incident reproduces exactly: export the event
range, run `ReplayRunner`, get byte-identical state and alerts. Bug reports are therefore
**a scenario file**, not a prose description — and a fixed bug becomes a permanent
regression test automatically. This is the main practical payoff of `ADR-0001`.


<!-- ==================================================================== -->
# FILE: docs/architecture/26-human-interaction.md
<!-- ==================================================================== -->

# Human Interaction Model

The user is a line cook with both hands occupied, under time pressure, who did not ask for
this system. Every design choice follows from that.

## Design constraints

1. **No dashboard.** There is no moment during service to inspect one.
2. **Glanceable in < 1 second.** Headline <= 6 words; required actions as icons + nouns.
3. **<= 2 taps to resolve anything.** Measured, not assumed (`34`).
4. **Silence is the default state** and is the feature that makes the rest tolerable.
5. **Never accusatory.** The system reports what it observed and did not observe; it never
   tells a person they contaminated something (`02`).
6. **No per-person feedback, ever.** No scores, no streaks, no "you forgot again." The
   moment the display becomes a performance instrument, cooperation ends (`24`).

## The three surfaces

### Tier 0 — Reset Prompt (the primary surface)

Appears at `TICKET_BOUND`, before any motion. A checklist:

```
  PINE NUT — station not clean
  [ ] New gloves
  [ ] Clean spreader
  ! Mayo container flagged — use sealed backup
```

Items **tick themselves off** as resets are observed. Compliance reads as progress, not
paperwork. This is the surface that carries most of the system's value and it must feel like
help, not interrogation.

### Tier 1 — Interrupt

A single line, dismissible, during prep. Fires only on `OBSERVED` pathways. Shows the
specific carrier and the specific action:

```
  STOP — spreader touched pesto.  [Swap tool]  [Already swapped]
```

### Tier 2 — Hold at the pass

The only blocking surface. Does not auto-clear. Shows the evidence trace (`25`) and the
epistemic disclaimer:

```
  HOLD — TICKET 48 — DO NOT SEND
  PINE_NUT. Spreader contacted pesto 14:31:52. Replacement not observed.
  This is an observation, not a determination. Confirm with the cook.
  [Cook confirms tool was clean]     [Remake]
```

## Worker actions

| Action | Effect | Grade |
|---|---|---|
| **Acknowledge** | Alert -> `ACKNOWLEDGED`. Does **not** clear taint. | — |
| **"Already swapped" / "Already clean"** | `OPERATOR_ASSERTION` -> taint cleared | `ASSERTED` |
| **Dismiss** (Tier 0/1 only) | Alert hidden for `t_cooldown`; state unchanged; logged | — |
| **Remake** | Ticket -> `VOIDED`, rework opened | — |
| **Resolve hold** (Tier 2) | Explicit human release. The only path out of `HELD`. | — |

Every action enters as an **event in the same log** (`10`) — replayable, auditable, and
part of the scenario suite. Corrections are not a side channel.

## What dismissal does and does not mean

Dismissal suppresses the *display*; it never clears *state*. A dismissed Tier 1 whose
pathway is still open will re-raise after cooldown, and will still escalate to Tier 2 at
completion. This is the one place the system deliberately does not defer to the human,
because the alternative is an instrument that can be silenced into uselessness — and Tier 2
is precisely the moment where a second opinion is cheapest relative to its cost.

Dismissal rate per carrier is tracked as a **system** health metric (is this zone badly
authored?), never as a **person** metric.

## Handling false alerts

The epistemic framing is what makes false alerts survivable. *"Replacement not observed"*
invites "I did swap it" -> one tap -> resolved. *"You contaminated this"* invites an
argument the system cannot win and a worker who stops trusting it.

Every assertion is logged with its grade, so a high assertion rate on one carrier surfaces a
perception defect rather than blaming an operator.

## Escalation to a second human

Tier 2 unresolved past `t_manager` surfaces to a manager. **Deferred post-MVP** — recorded
because the alert model (`16`) already reserves the transition.


<!-- ==================================================================== -->
# FILE: docs/engineering/30-repository-layout.md
<!-- ==================================================================== -->

# Repository Layout

Every directory must justify its existence. No premature services, no speculative packages.

```
/
  CLAUDE.md                 project context + pointers (root, auto-loaded)
  README.md                 what this is, how to run it
  docs/                     the specification (see docs/README.md)
  config/
    station/<id>.yaml       zones, calibration, carriers, thresholds
    knowledge/<rest>/       allergen taxonomy, ingredients, menu items
    profiles/{dev,demo,eval,prod}.yaml
  scenarios/                executable replay fixtures (scenario A-M + regressions)
  data/                     gitignored. recordings, annotations, eval outputs
  experiments/              experiment code + results (never imported by src/)
  scripts/                  calibration, fixture authoring, eval runners
  src/
    domain/                 pure types. ZERO internal dependencies.
    events/                 event schemas, log, serialization        <- THE BOUNDARY
    knowledge/              taxonomy, ingredient map, recipes
    state/                  reducer: (WorldState, Event) -> WorldState
    risk/                   pathway search, precondition check
    policy/                 tier selection, alert lifecycle
    orders/                 ticket lifecycle, normalization, binding
      adapters/             the ONLY place a third-party order schema may appear
    perception/             frames -> detections -> tracks -> events
    replay/                 scenario loader, deterministic runner
    runtime/                composition root, clock, modes, health
    ui/                     worker display, inspector
  tests/
    unit/ domain/ state/ risk/ policy/ orders/
    replay/                 runs every /scenarios fixture
    perception/             fixture-based event-level scoring
    integration/
    property/               invariants from `11`
```

## Dependency rules (CI-enforced)

1. `domain/` imports nothing internal.
2. `perception/` may import **only** `domain/` and `events/`.
3. `state/`, `risk/`, `policy/`, `orders/` may **not** import `perception/`, `ui/`, or
   `runtime/`.
4. `runtime/` is the only composition root; it is the only module permitted to import
   broadly.
5. `experiments/` may import `src/`; `src/` may **never** import `experiments/`.
6. Direct clock/`now()` access is forbidden outside `runtime/` (`19`).

Violations fail the build. These rules are the mechanical form of the
perception/safety separation mandated in `10`; left to convention they will decay within
days.

## Why no microservices

One process, one station. Splitting introduces serialization boundaries, partial failure,
and clock skew — all of which make deterministic replay harder — in exchange for scaling we
do not need. Multi-station aggregation, if ever built, is a **read-only consumer of exported
event logs**, not a decomposition of the runtime.


<!-- ==================================================================== -->
# FILE: docs/engineering/33-testing-strategy.md
<!-- ==================================================================== -->

# Testing Strategy

Written before implementation, deliberately. The test hierarchy is what allows the safety
core to be finished and verified before a camera exists.

## Levels — and what each *proves*

| Level | Input | Proves | Gate for |
|---|---|---|---|
| **Unit** | Functions | Component correctness | every phase |
| **Property** | Generated event sequences | Invariants from `11` hold universally: determinism; taint monotonic between resets; every taint has a source event; `hops` strictly increases; reducer output invariant to `confidence` | P1 |
| **Domain** | Taxonomy + ingredient fixtures | Closure and resolution correctness, incl. `may_contain` strength | P2 |
| **State transition** | Hand-built event sequences | Every row of the `13` transition table, **including the ones that must do nothing** (`SURFACE_WIPE`) | P1 |
| **Risk engine** | Hand-built `WorldState` + tickets | Pathway search: direct, tool, surface, back-contamination, hop limit, reset-breaks-path, temporal ordering | P1 |
| **Policy** | `RiskAssessment` sequences | Tier selection, `alert_key` dedup, escalation timing, cooldown, suppression logging | P1 |
| **Replay / scenario** | `/scenarios/*.yaml` | **End-to-end reasoning with zero perception.** All of A-M. The backbone. | P1, P3 |
| **Perception** | Annotated video fixtures | Event-level precision/recall per event type; occlusion reporting honesty | P4, P5 |
| **Integration** | Recorded video + fixture tickets | Camera -> events -> alert, wired | P4 |
| **End-to-end** | Live station | The demo path | P6 |
| **Adversarial** | Scenarios K-M + fuzzed logs | Identity switch, camera fault, alert storms, malformed events | P4+ |

## The replay suite is the backbone

Every product scenario (`product/03-scenarios.md`) is an executable fixture. Every bug
becomes a fixture. Every failure mode in `23` maps to a fixture or an offline metric, and a
meta-test asserts that mapping is **total** — a failure mode with no test is a tracked
defect, not an oversight.

## Required negative tests

Easy to forget, and each guards a claim the product makes:

- Scenario A asserts **silence** — no alert, no prompt.
- `SURFACE_WIPE` asserts **no state change**.
- Below-threshold normalizer input asserts **never** `RESOLVED`.
- `BLOCKED -> BOUND` asserts **unreachable**.
- Alert copy lint asserts prohibited claim words never appear in any template (`02`).
- Serialization asserts **no event type can carry binary data** (`24`).
- Determinism asserts every fixture run twice produces byte-identical output.

## What is deliberately not tested

Cleaning efficacy, food identity, and anything requiring ground truth about actual protein
transfer. These are outside the system's claims (`02`); tests asserting them would imply
capabilities the product denies having.


<!-- ==================================================================== -->
# FILE: docs/engineering/37-demo-plan.md
<!-- ==================================================================== -->

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


<!-- ==================================================================== -->
# FILE: docs/engineering/38-workflow.md
<!-- ==================================================================== -->

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


<!-- ==================================================================== -->
# FILE: docs/engineering/39-implementation-plan.md
<!-- ==================================================================== -->

# Implementation Plan

Source of truth for **technology selection and build order**. `32-dependency-policy.md` owns
the *principles*; this document owns the *choices* made under them. Architecture is fixed
(`docs/architecture/`); nothing here may change a contract.

---

## 1. Language and process

**Python 3.11+, single process, single language.**

The safety core is algebraic types, state machines, graph search, and property tests — all of
which Python does adequately with `frozen dataclass` + `Enum` + `mypy --strict`. Perception
is unavoidably Python (every vision library lives there). Splitting the core into a
better-typed language would buy stronger guarantees at the cost of an IPC boundary,
serialization, and two toolchains — a tax with no payoff at one station (`ADR-0012`).

**Concurrency model:**

```
  [perception thread]                    [asyncio event loop, main thread]
  capture -> detect -> assemble          drain queue -> reorder -> append log
         |                                      -> reduce -> risk -> policy
         +--> queue.Queue(DraftEvent) ---->     -> broadcast state over WebSocket
                                                -> serve UI, accept worker actions
```

One perception thread (OpenCV and MediaPipe release the GIL during native work, so this
genuinely parallelizes), one asyncio loop for runtime + web. No multiprocessing: shared
state across processes would undermine the determinism that `ADR-0001` depends on.

## 2. Dependencies

Small by design. **No PyTorch, no YOLO, no GPU.** The whole system runs on a laptop CPU.

| Group | Package | Version | Why |
|---|---|---|---|
| **core** | `pydantic` | ~2.9 | Event schemas, validation, JSON (de)serialization, discriminated unions on `type`, generated JSON Schema. Rust-backed, fast. |
| **core** | `pyyaml` | ~6.0 | Config + scenario files |
| **runtime** | `fastapi` | ~0.115 | HTTP + WebSocket |
| **runtime** | `uvicorn` | ~0.32 | ASGI server |
| **perception** | `opencv-python` | ~4.10 | Capture, homography, **ArUco**, HSV segmentation, contours |
| **perception** | `numpy` | ~2.1 | Array ops |
| **perception** *(optional)* | `mediapipe` | ~0.10 | Hand landmarks, only if HSV proves insufficient |
| **dev** | `pytest`, `pytest-asyncio` | — | Tests |
| **dev** | `hypothesis` | ~6.x | Property tests for `11` invariants |
| **dev** | `import-linter` | ~2.0 | **Enforces the layer DAG** (`30`) |
| **dev** | `mypy` | ~1.11 | `--strict` on `domain/ events/ state/ risk/ policy/` |
| **dev** | `ruff` | ~0.7 | Lint + format |

`pip install -e .` installs core + runtime only. Perception and dev are extras:
`.[perception]`, `.[dev]`. **The safety core must be testable without a camera library
installed** — this is the practical test of `ADR-0001`, and CI runs the core suite in an
environment where `opencv` is absent.

## 3. Perception: how each obligation in `21` is met

The architecture removed food recognition (`ADR-0007`), which collapses this to geometry.

| Obligation | Technique | Why this, not a learned model |
|---|---|---|
| **Station frame** | 4 ArUco markers taped at table corners -> `cv2.findHomography` -> pixel↔mm | 20 lines, sub-mm stable, recalibrates in seconds |
| **Zones** | Polygons in mm, authored once; `cv2.pointPolygonTest` | Config, not perception (`ADR-0007`) |
| **Gloves / hands** | **HSV colour segmentation** + contour + centroid | Nitrile gloves are strongly saturated (blue/purple) against a white/steel surface. Deterministic, ~2ms/frame, explainable, zero training data. Kitchens already colour-code allergen equipment — we exploit the environment instead of fighting it. |
| **Tools** | **ArUco marker (4x4, 25mm) on each handle** | Gives *guaranteed identity*, which nearly eliminates failure mode P3 (identity switch) and therefore the pessimistic merges that drive Tier 0 noise — a direct mitigation of risk **A6**. |
| **Boards / containers** | Fixed zones + ArUco for swappable boards | Same |
| **Contact** | Blob centroid ∈ polygon, or blob∩blob, held ≥ `t_dwell` with hysteresis | Directly implements the predicate in `20` |
| **Occlusion** | Track absent > `t_occlusion_max` -> `CARRIER_OBSERVABILITY_CHANGED` | The honesty obligation in `21` |
| **Glove change** | `ZONE_ENTRY(glove_dispenser)` + hand-absence ≥ 2s + reappearance -> `GLOVE_CHANGE` at **`INFERRED`** grade | Weakest detector in the system; graded honestly. Operator assertion is always the fallback. Tracked as `EXP-004`. |
| **Health** | Frame starvation, static-frame, exposure stats -> `HEALTH_DEGRADED` | Drives `PROTOCOL_ONLY` (`ADR-0011`) |

**On ArUco markers.** They are an implementation choice, not an architectural dependency —
`20` explicitly lists fiducials as *not required*, so a learned detector can be swapped in
behind the same contract. The defence is not convenience: guaranteed tool identity removes
the most dangerous perception failure (taint attributed to the wrong tool), and a sticker on
a handle is a smaller operational ask than the colour-coded allergen equipment kitchens
already buy. If time permits, add a marker-free detector as a *second* path so the demo can
show both.

Resolution 1280x720 @ 15fps. `t_dwell` = 250ms gives ~4 frames of confirmation.

## 4. Core data structures

```python
# events/ — pydantic discriminated union
Event = Annotated[Union[ZoneEntry, ContactBegin, GloveChange, ...],
                  Field(discriminator="type")]

# state/ — the ADR-0004 enforcement mechanism
@dataclass(frozen=True)
class GradedEvent:          # projection of Event with `confidence` REMOVED
    ...                     # the reducer's signature is what enforces the rule

def reduce(state: WorldState, e: GradedEvent, cfg: Config) -> tuple[WorldState, list[StateDelta]]

# risk/ — the contact graph, kept incrementally by the reducer
contacts: dict[CarrierId, list[ContactEdge]]   # (t, other, event_id), time-ordered
resets:   dict[CarrierId, list[Timestamp]]
```

**Pathway search** (backward BFS, ~60 lines, bounded by `max_hops` × ~10 active carriers):

```
find_pathways(target, allergens, t_now):
  frontier = [(target, t_now, [])]
  for hop in range(max_hops):
    for (carrier, t_upper, path) in frontier:
      for (t, other, eid) in contacts[carrier] where t < t_upper:
        if any reset on carrier within (t, t_upper): continue      # path broken
        if other is INGREDIENT zone and allergens_of(other) ∩ allergens:
            yield path + [edge]                                     # source reached
        else: extend frontier with (other, t, path + [edge])
```

Time ordering and reset-breaking are the loop conditions — there is no correlation window and
no tuned fuzz factor, which is why this needs no training and no calibration.

## 5. Storage and formats

| Artifact | Format | Why |
|---|---|---|
| Event log | **JSONL**, one file per session | Append-only by construction, human-readable, git-diffable, replayable with `cat`. No database needed. |
| Scenarios | YAML (`36`) | Hand-authored specification |
| Station + knowledge config | YAML + Pydantic validation | `31` |
| Eval reports | JSON in `data/eval/<date>/` | The gate evidence artifacts (`38`) |
| Frames | **Never written** (prod) | `24` |

## 6. UI

**FastAPI + WebSocket + a single vanilla HTML/CSS/JS page.** No build step — a bundler is
pure tax for three surfaces and a carrier grid.

- Server pushes **full state** at 5Hz over WebSocket (~2KB; deltas are premature optimization)
- Client posts `/action` -> becomes an `OPERATOR_ASSERTION` event in the log (`10`)
- Two routes: `/` worker display, `/inspector` read-only state + event timeline (`25`)

The carrier grid — tiles going amber as taint spreads — is the demo's core visual and is
built in **P3, not P6** (`37`).

### 6.1 Toolkit — and what we are deliberately avoiding

**No component library.** Component libraries are the thing that produces the generic
"AI-generated app" look — Tailwind defaults, shadcn cards, `rounded-lg` everywhere, Inter,
a purple-blue gradient. Distinctiveness comes from palette and type, which we already have.

| Need | Choice | Note |
|---|---|---|
| Design tokens | **Open Props** (single CSS file, no build) | Gives a coherent scale of sizes, easings, shadows without imposing components |
| Icons | **Phosphor Icons** | Deliberately *not* Lucide — Lucide is shadcn's default and is the single most recognisable marker of generated UI |
| Type | Archivo + IBM Plex Sans/Mono | Already chosen (`39.1`); the strongest anti-default signal on the page |
| Video overlay | **Plain SVG**, absolutely positioned over the `<video>` element | Animates with CSS classes. No library. The published mockup proves the approach. |
| Charts | none | This UI has no charts. Do not add one. |
| Live updates | WebSocket + full state at 5Hz | No library |

**Vendor every asset into `ui/static/`.** Venue wifi fails, and a CDN miss during the demo
is a black screen. No runtime network dependency of any kind.

### 6.2 The aesthetic direction

The reference is **industrial HMI — a glass cockpit or a kitchen display terminal — not web
SaaS.** That direction is what actually prevents the templated look, more than any library
choice. Concretely:

- Border radius **2-3px maximum**. Never 8-12px.
- **No box-shadows** on data surfaces; separate with 1px borders instead.
- **No gradients** anywhere.
- Monospace for every number and identifier, with `tabular-nums`.
- State encoded as **thick left borders and fills**, not rounded badge pills.
- Uppercase micro-labels with wide letter-spacing for field names.
- High-contrast dark ground — the station display commits to dark deliberately, because
  that is what a real kitchen display is. It is the one surface that does not follow the
  viewer's theme.

The published station-display mockup already implements all of this and is the approved
reference; match it rather than re-deriving it.

## 7. Enforcing the architecture mechanically

| Rule | Mechanism |
|---|---|
| Layer DAG (`22`) | `import-linter` contract in `pyproject.toml`; CI failure |
| No clock outside `runtime/` (`19`) | pytest AST walk over core packages for `time.*`/`datetime.now` |
| No `confidence` in the reducer (`ADR-0004`) | `GradedEvent` type + property test: mutate confidence, assert identical output |
| No binary data in events (`24`) | Serialization test over every event type |
| No prohibited claim words (`02`) | Lint over alert copy templates |
| Determinism (`36`) | Every fixture run twice in CI, outputs diffed |

Each is a test, not a review convention. Conventions decay within days.

## 8. Build order and parallelization

The event-log boundary is what makes this parallel. After schemas land (~2h), **four streams
run independently** and only meet at integration.

| Stream | Phases | Depends on | Can start |
|---|---|---|---|
| **A — Core** | P0 -> P1 -> P2 | — | hour 0 |
| **B — Perception** | P4 -> P5 | event schemas only | hour 2 |
| **C — Interface** | P3 | event schemas only (mock state) | hour 2 |
| **D — Content** | scenarios, knowledge bundle, station build, recordings | — | hour 0 |

| Phase | Est. | Output |
|---|---:|---|
| P0 Contracts | 2h | Types, schemas, log, config loader, lints |
| **P1 Reasoning core** | **5h** | Reducer, pathway search, tiers, alerts, replay runner, 13 fixtures green |
| P2 Orders & knowledge | 2h | Normalizer with `AMBIGUOUS`, taxonomy, recipes |
| P3 UI + `PROTOCOL_ONLY` | 4h | Three surfaces, carrier grid, evidence trace |
| P4 Perception: zones/contact | 5h | Calibration, HSV gloves, contact episodes, occlusion |
| P5 Perception: tools/resets | 3h | ArUco tools, swaps, glove change |
| P6 Demo hardening | 3h | Frozen calibration, fallbacks, 5 clean runs |

~24 focused hours; ~14h on the critical path with four people.

**Estimated total: ~3,900 LOC** (core ~1,700, perception ~600, UI ~400, tests ~800,
scripts ~400).

## 9. The cut line

> **Ship P0-P3. Everything after is upside.**

At the end of P3 there is a complete, demoable, honest product running in `PROTOCOL_ONLY`
with no camera attached: tickets bind, Tier 0 fires with recipe-scoped checklists, workers
resolve in one tap, Tier 2 holds work, evidence traces render. That is a real product and a
real demo.

P4-P5 add the observation that makes it compelling. They are **not** load-bearing for having
something to show — which is the entire point of building the core first.

## 10. Hardware

Folding table · overhead camera (USB webcam on a boom, or an iPhone via Continuity Camera —
better optics, free) · 4 labelled bins · cutting board · spreader · glove box · clean-tool
rack · printed ArUco markers · laptop or tablet for the display. **Marginal cost ≈ $0.**

## 11. Top implementation risks

| Risk | Mitigation | Fallback |
|---|---|---|
| HSV glove segmentation fails under venue lighting | `scripts/tune_hsv.py` live slider tool; calibrate at the venue, not at home | MediaPipe Hands; failing that, ArUco wristband |
| Glove-change detection unreliable (`EXP-004`) | Graded `INFERRED`, never `OBSERVED` | Operator assertion — already a designed path, not a patch |
| Camera dies during the demo | Rehearsed drill | `PROTOCOL_ONLY` -> recorded log -> `scenarios/demo.yaml`, all producing identical UI |
| P1 overruns | It is the critical path and the novel part; staff it with the strongest person | Nothing else may start before it — this is deliberate |
| Scope creep into food recognition | `ADR-0007`; reviewers reject on sight | — |

