# HANDOFF BUNDLE — PERCEPTION

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
# FILE: docs/architecture/12-event-model.md
<!-- ==================================================================== -->

# Event Model

Events are the **sole contract** between perception and safety reasoning. Raw detections
never drive alerts (`ADR-0002`).

## Common envelope

Every event carries:

```
event_id      : Id            # monotonic, sortable, globally unique (format TBD at P0)
seq           : int           # per-station commit sequence, gapless
type          : EventType
t_occurred    : Timestamp     # station clock, when the physical thing happened
t_committed   : Timestamp     # when the log accepted it (see `19`)
station_id    : StationId
schema_version: int
source        : PERCEPTION | OPERATOR | ORDER_SYSTEM | SYSTEM
confidence    : float?        # raw score. METADATA ONLY.
grade         : EvidenceGrade # OBSERVED | INFERRED | ASSERTED | PESSIMISTIC
evidence      : EvidenceRef   # track ids, zone ids, frame range. NEVER pixels.
mutates_state : bool          # static per type; see table
```

> **Hard invariant:** the reducer may branch on `grade`. It may **never** branch on
> `confidence`. The float exists for evaluation and assembler tuning only. Enforced by the
> reducer's function signature (it receives a `GradedEvent` projection without the float)
> and by a unit test asserting reducer output is invariant to `confidence`. See `ADR-0004`.

## Catalog

### Contact events (perception-sourced, mutate state)

| Type | Required fields | Mutates | Notes |
|---|---|---|---|
| `CONTACT_BEGIN` | `a: CarrierId`, `b: CarrierId \| ZoneId`, `contact_point` | yes | Fires once per contact episode after `t_dwell` |
| `CONTACT_END` | `a`, `b`, `duration_ms` | no | Closes the episode; feeds dedup windows |
| `ZONE_ENTRY` | `carrier`, `zone`, `depth` | yes | A hand entering an ingredient bin; the taint acquisition primitive |
| `ZONE_EXIT` | `carrier`, `zone`, `dwell_ms` | no | |

A contact **episode** is `BEGIN`..`END`. Continuous contact produces one episode, not N
frames of events — this is where the "40 alerts in 10 seconds" problem is solved, at the
assembly layer rather than the alert layer (`16`).

### Reset events (mutate state — the only taint-clearing events)

| Type | Required fields | Grade | Clears |
|---|---|---|---|
| `GLOVE_CHANGE` | `worker_slot`, `phase: DOFF \| DON` | `OBSERVED` | `GLOVES` taint, on `DON` |
| `TOOL_SWAP` | `retired: CarrierId`, `introduced: CarrierId`, `from_zone` | `OBSERVED` | introduced carrier starts from `CLEAN_STOCK` state |
| `SURFACE_SWAP` | `retired`, `introduced`, `from_zone` | `OBSERVED` | as above |
| `WASH_CYCLE` | `carrier`, `zone: WASH`, `duration_ms` | **`ASSERTED`** | taint, at reduced grade — efficacy is unobservable |
| `OPERATOR_ASSERTION` | `carrier`, `claim: CLEAN \| REPLACED`, `worker_slot` | **`ASSERTED`** | taint, grade `ASSERTED` |

### Recorded-but-non-clearing

| Type | Mutates | Why it exists |
|---|---|---|
| `SURFACE_WIPE` | **no** | Wiping redistributes protein; it is not a reset (`14`). Recorded for audit and to show the worker *why* the prompt persisted. |

This is the single most counter-intuitive event in the system. It is logged prominently and
tested explicitly (scenario J) precisely because a future contributor will be tempted to
make it clear taint.

### Ticket events (order-sourced)

`TICKET_RECEIVED`, `TICKET_RESTRICTION_RESOLVED`, `TICKET_BLOCKED`, `TICKET_BOUND`,
`TICKET_PREP_STARTED`, `TICKET_ITEM_COMPLETE`, `TICKET_HELD`, `TICKET_RELEASED`,
`TICKET_VOIDED`, `TICKET_REWORK_OPENED`.

Only `TICKET_BOUND` / `TICKET_ITEM_COMPLETE` / `TICKET_RELEASED` affect risk evaluation
timing; the rest are lifecycle bookkeeping.

### System events

| Type | Purpose |
|---|---|
| `STATION_MODE_CHANGED` | Mode is state, therefore it must be an event (`10`) |
| `CARRIER_OBSERVABILITY_CHANGED` | `TRACKED -> STALE -> UNKNOWN` transitions, with cause |
| `TRACK_IDENTITY_SUSPECT` | Tracker cannot distinguish two carriers -> triggers pessimistic merge |
| `CONFIG_LOADED` | Stamps `config_version` + `knowledge_version` into the log for replay fidelity |
| `HEALTH_DEGRADED` | Camera fault, frame starvation, reducer exception |

### Alert events (policy-sourced)

`ALERT_RAISED`, `ALERT_UPDATED`, `ALERT_ACKNOWLEDGED`, `ALERT_RESOLVED`,
`ALERT_ESCALATED`, `ALERT_EXPIRED`. Carry `alert_id` + `pathway_signature` (`16`).

## Causality

Events do not carry parent pointers — causality is **reconstructed** from the log rather
than asserted at emission time, because emission-time causality would require perception to
reason about semantics. Instead:

- `TaintRecord.source_event_id` records which event introduced a taint
- `Alert.derivation` is an ordered list of `(event_id, rule_id, state_delta)`
- Together these yield the full evidence trace (`25`) without any event needing to know
  what will later depend on it

## Lifecycle

Events are **immutable and append-only**. Corrections are new events (e.g.
`OPERATOR_ASSERTION`), never edits. Late-arriving perception events are held in a reorder
window of `t_reorder` (default 500ms) and sorted by `t_occurred` before commit; after
commit, order is final (`19`).

## Schema governance

Schemas are versioned per-event-type. A schema change requires a version bump and a
migration note. Replay fixtures record the schema version they were authored against;
loading an older fixture applies forward-migrations so **old scenarios keep passing**. This
is what stops the golden-test suite from rotting.


<!-- ==================================================================== -->
# FILE: docs/architecture/19-temporal-model.md
<!-- ==================================================================== -->

# Temporal Model

Time is load-bearing here: the entire product distinguishes sequences that contain the same
events in different orders.

## Clocks

| Clock | Source | Used for |
|---|---|---|
| `t_occurred` | Station monotonic clock, captured at frame acquisition | **All reasoning.** Ordering, windows, staleness |
| `t_committed` | Log commit time | Latency measurement and debugging only |
| Wall clock | OS | Display and audit export only |

> **Invariant: no code in layers 6-11 may read a wall clock.** Time is injected as a `Clock`
> interface and, in replay, is driven entirely by `t_occurred` in the log. This is what
> makes replay bit-deterministic, and it is extremely painful to retrofit — it is enforced
> from P0 by a lint rule banning direct clock imports outside `runtime/`.

## Ordering and the reorder window

Perception can emit slightly out of order (variable inference latency across parallel
detectors). The log holds incoming events for `t_reorder` (default 500ms), sorts by
`t_occurred`, then commits with a gapless `seq`.

After commit, order is **final**. An event arriving later than `t_reorder` is committed at
the tail with `late: true` and flagged; the reducer processes it normally but the
observability layer surfaces late events because a rising late-rate is the leading indicator
of perception falling behind.

## "Did B happen after A, and could A have caused B?"

The system answers this **structurally, not heuristically**:

- `t(A) < t(B)` strictly, using `t_occurred`
- A and B share a carrier node
- No valid reset on that carrier in `(t(A), t(B))`

That conjunction *is* the pathway edge condition (`14`). There is no correlation window, no
"within N seconds" fuzz, and no learned causality. A reset at any point in between breaks
the chain regardless of how close in time the events were — which is the correct semantics
and also the reason the model needs no tuning parameter here.

## Windows

> **Values below are informative.** `engineering/31-configuration.md` is authoritative for
> defaults; this table exists to explain what each window *means*. If they disagree, `31`
> wins and this table is the defect.

| Window | Default | Purpose |
|---|---|---|
| `t_dwell` | 250ms | Minimum zone dwell to emit `ZONE_ENTRY` — rejects pass-throughs |
| `t_hysteresis` | 400ms | Contact must be absent this long before `CONTACT_END` — prevents flicker |
| `t_reorder` | 500ms | Log reorder buffer |
| `t_stale[kind]` | 20s / 120s / 300s / 600s | Epistemic decay (`13`) |
| `t_occlusion_max` | 3s | Occlusion beyond this -> `UNKNOWN`, not `STALE` |
| `station_recent_window` | 30m | Pessimistic closure scope |
| `t_escalate` | 20s | Tier 1 -> Tier 2 |
| `t_cooldown` | 120s | Post-assertion suppression |
| `t_abandon` | 15m | Ticket auto-void |

All are configuration (`31`), all are recorded in `CONFIG_LOADED`, and a replay uses the
recorded values — otherwise retuning a threshold would silently change what old fixtures
assert.

## Concurrent preparation

No temporal interleaving logic is required, because taint is carrier-held (`17`). Two
overlapping tickets share one carrier timeline; each ticket queries that timeline through
its own restriction filter.


<!-- ==================================================================== -->
# FILE: docs/architecture/20-spatial-model.md
<!-- ==================================================================== -->

# Spatial Model

Stated as **requirements on information**, not as a choice of vision method. Any technique
that satisfies this contract is acceptable (`21`).

## Station frame

A 2D planar coordinate system fixed to the work surface, in millimetres, origin at a
physical fiducial on the station. All spatial reasoning happens in this frame — never in
pixel coordinates — so that camera movement, resolution changes, or a different lens are
recalibration, not a data-model change.

Established once during `CALIBRATION` mode and stored as `station_config.calibration`,
versioned. A calibration change invalidates recorded fixtures and must bump
`config_version`.

## Zones

```
Zone { zone_id, polygon: List<Point2D>, kind, contents, bound_carrier }
```

Zone kinds: `INGREDIENT`, `TOOL_RACK`, `CLEAN_STOCK`, `WORK`, `LANDING`,
`GLOVE_DISPENSER`, `WASH`.

Zones are **configuration, authored once**. This is the decision that makes the whole
perception problem tractable: the system never asks "what substance is this," it asks "did a
tracked entity enter polygon 7," and configuration supplies the meaning (`ADR-0007`).

Zones may overlap. When a contact point falls in multiple zones, **all** matching zones
receive a contact event; the reducer's union semantics make this safe by construction rather
than requiring a tie-break rule.

## What the architecture requires

| Requirement | Why |
|---|---|
| Stable planar coordinate frame | Zone membership must mean the same thing over time |
| Polygonal zone membership test | Contact predicate |
| A contact point (or small region) per tracked entity | The thing tested against zones |
| Stable entity identity across frames | Taint must follow the right carrier |
| Occlusion signal | Drives epistemic degradation (`13`) |

## What it explicitly does **not** require

Depth sensing, 3D pose, hand keypoints, food classification, material recognition, multiple
cameras, or fiducial markers on tools. Each of these is a possible improvement; none may
become a hidden dependency. If a design begins to need one, that is an ADR, not an
implementation detail.

## Contact predicate

```
contact(entity, zone) := point_in_polygon(entity.contact_point, zone.polygon)
                         AND dwell >= t_dwell
                         AND hysteresis satisfied
```

Carrier-to-carrier contact uses region intersection over `t_dwell` in the same frame.

## Known spatial limitations (recorded, not hidden)

- A hand passing **over** a bin without entering it is indistinguishable from entering it
  under a purely 2D overhead projection. Mitigated by `t_dwell` and, if needed, a depth
  signal — deferred, tracked in `experiments/`.
- Zone boundaries are crisp; physical reality is not. Contact near an edge is decided by the
  polygon, which can be wrong in both directions. Zones should be authored slightly
  **generous** for `INGREDIENT` kinds (false contact -> Tier 0, cheap) and slightly
  **conservative** for `CLEAN_STOCK` (false reset would be dangerous). This asymmetry is a
  documented authoring rule in `31`.


<!-- ==================================================================== -->
# FILE: docs/architecture/21-perception-contract.md
<!-- ==================================================================== -->

# Perception Contract

Defines what perception **must produce**. It deliberately says nothing about how.

## Obligations

Perception must emit, into the log, with `t_occurred` in station time:

1. `ZONE_ENTRY` / `ZONE_EXIT` for tracked entities against configured zones
2. `CONTACT_BEGIN` / `CONTACT_END` between tracked carriers
3. `CARRIER_OBSERVABILITY_CHANGED` whenever a carrier becomes unobservable or re-observed
4. `TRACK_IDENTITY_SUSPECT` whenever it cannot distinguish two carriers
5. `GLOVE_CHANGE`, `TOOL_SWAP`, `SURFACE_SWAP`, `SURFACE_WIPE`, `WASH_CYCLE` where detectable
6. `HEALTH_DEGRADED` on frame starvation, exposure failure, or occlusion of the station

## Obligations of honesty (the important half)

- Perception must report **not knowing**. Failing to emit
  `CARRIER_OBSERVABILITY_CHANGED` when a carrier is lost is a **more serious defect** than a
  false detection, because the safety core's conservatism depends entirely on being told.
- Perception must never suppress an observation because it seems implausible. Plausibility
  is the reasoning layer's concern.
- Every emitted event carries an honest `confidence` (metadata) and a `grade` derived from
  configured thresholds.

## Grade assignment

```
confidence >= threshold_observed[type]  -> OBSERVED
confidence >= threshold_inferred[type]  -> INFERRED
otherwise                                -> not emitted
```

Thresholds are per-event-type configuration, tuned against the evaluation fixtures (`34`),
and recorded in `CONFIG_LOADED`. **Below-threshold observations are dropped, not
downgraded** — because an unbounded stream of low-grade events would inflate the pessimistic
closure into permanent noise. The safety net for what perception drops is epistemic
degradation, not weak events.

## Non-obligations

Perception is **not** responsible for: identifying substances, knowing allergens, knowing
which ticket is active, deciding whether contamination occurred, judging cleaning efficacy,
or any tier decision. If a perception module imports from `state/`, `risk/`, `policy/`, or
`orders/`, the import lint fails the build (`30`).

## Degradation ladder

| Condition | Emission |
|---|---|
| Entity occluded < `t_occlusion_max` | nothing; tracker interpolates |
| Occluded >= `t_occlusion_max` | `CARRIER_OBSERVABILITY_CHANGED -> UNKNOWN` |
| Two carriers confusable after occlusion | `TRACK_IDENTITY_SUSPECT` |
| Frame rate below floor / camera fault | `HEALTH_DEGRADED` -> runtime enters `PROTOCOL_ONLY` |


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
# FILE: docs/architecture/23-failure-modes.md
<!-- ==================================================================== -->

# Failure Modes

## Governing principle

> Every perception failure maps to an **epistemic degradation**; every epistemic degradation
> maps to the **cheapest intervention**.

That single rule contains most of this taxonomy. The system is designed so that being wrong
is inexpensive, rather than trying to be right more often.

## Taxonomy

Legend — **D**etection, **C**onsequence, **Ct**ainment, **F**allback, **L**og, **R**ecovery.

### P1 Missed detection (contact occurred, no event emitted)
- **D** Not directly detectable at runtime. Measured offline against annotated fixtures (`34`).
- **C** Taint not recorded -> potential silent miss.
- **Ct** Tier 0 fires on *preconditions*, not on detections, so the most common hazard
  (starting a restricted ticket on a dirty station) is caught by **policy**, which has no
  miss rate. Pessimistic closure covers unobserved periods.
- **F** `PROTOCOL_ONLY` if misses correlate with a health signal.
- **L** Offline: event-level recall per fixture.
- **R** Retune thresholds; add fixture; re-run gate.

### P2 False detection (event emitted, nothing happened)
- **D** Offline precision; runtime proxy = alert-per-hour rate.
- **C** Spurious taint -> Tier 0 prompt (8s) or, if `OBSERVED`, a Tier 1 interrupt.
- **Ct** Grade thresholds; `t_dwell`; hysteresis; episode collapsing.
- **F** Worker taps "Already clean" -> `OPERATOR_ASSERTION`, one tap, logged.
- **L** Assertion rate per carrier is the nuisance signal; a spike localizes a bad zone.
- **R** Re-author the zone polygon; raise `t_dwell`.

### P3 Identity switch (tracker swaps two carriers)
- **D** Implausible motion, re-entry after occlusion, overlapping bounding regions.
- **C** **Taint attributed to the wrong carrier — the most dangerous perception failure**,
  because it can make a dirty tool appear clean.
- **Ct** `TRACK_IDENTITY_SUSPECT` -> **pessimistic merge** of both taint sets, both -> `STALE`.
  Never a silent reassignment.
- **F** Merge makes both carriers suspect -> Tier 0 on next bind.
- **L** Suspect rate; merged-carrier pairs.
- **R** Increase visual distinctiveness of tools (colour-coded allergen equipment, which
  operators already use); add a fixture.

### P4 Occlusion
- **D** Track lost > `t_occlusion_max`.
- **C** Unobserved interval.
- **Ct** -> `UNKNOWN` -> pessimistic closure -> Tier 0. **This is scenario H and it is a
  designed-for path, not an error.**
- **L** Occlusion duration histogram per carrier; a persistently occluded zone is a camera
  placement defect, surfaced in the inspector.

### P5 Camera fault / obstruction / lighting collapse
- **D** Frame starvation, exposure statistics, static-frame detection.
- **C** Total loss of perception.
- **Ct/F** `HEALTH_DEGRADED` -> `PROTOCOL_ONLY`. **Tier 0 continues; the product retains
  its primary value.** UI states plainly that vision is unavailable.
- **R** Automatic return to `FULL` after `t_recover` of healthy frames, via
  `STATION_MODE_CHANGED`. All carriers remain `UNKNOWN` until individually re-observed —
  recovery never restores trust it did not earn.

### P6 Unknown ingredient in a zone
- **C** Cannot resolve allergens.
- **Ct** `UNKNOWN_ALLERGEN_PROFILE` — treated as possibly containing **any** restricted
  allergen. Tier 0.
- **R** Setup-time validation refuses to start a station whose zone contents are unresolvable
  against the knowledge bundle, so this is caught at calibration rather than service.

### P7 Missing / ambiguous order information
- **Ct** `AMBIGUOUS` -> binding blocked -> resolution request. Scenario G. **Never guess.**

### P8 Ambiguous action (was that a wipe or a swap?)
- **Ct** Below-threshold reset events are **not emitted**. An unrecognized reset therefore
  leaves taint in place -> a prompt the worker can clear in one tap.
- **Rationale** A missed reset costs 8 seconds; a falsely-detected reset silently clears real
  contamination. The asymmetry dictates the threshold direction, and it must be documented
  because it looks like over-conservatism until you see why.

### P9 Stale state
- **Ct** Epistemic axis (`13`); `t_stale` per carrier kind.

### P10 Corrupted / schema-invalid event
- **Ct** Rejected at `append`, `HEALTH_DEGRADED` emitted, runtime continues. A malformed
  perception event may never crash the safety core.
- **R** Rejected events are written to a quarantine log for offline diagnosis.

### P11 Reducer / risk-engine exception
- **Ct** Catch at the runtime boundary -> `PROTOCOL_ONLY`, existing Tier 2 holds **persist**,
  incident logged with the triggering `event_id` for deterministic reproduction.
- **Never fail open to silence.** A crashed safety core that shows a clean screen is the
  worst possible outcome; the UI must visibly state that reasoning is down.

### P12 Config / knowledge mismatch
- **D** Checksum + version validation at load.
- **Ct** Refuse to enter `FULL`; remain in `CALIBRATION` with a clear error. Safety-critical
  config never loads partially.

## Failure-mode coverage matrix

Every row above has a corresponding fixture in `/scenarios/` or an offline metric in `34`.
`engineering/33-testing-strategy.md` asserts the mapping is total — a failure mode with no
test is itself a tracked defect.


<!-- ==================================================================== -->
# FILE: docs/architecture/24-privacy-security.md
<!-- ==================================================================== -->

# Privacy and Security

Privacy here is an **adoption requirement**, not a compliance checkbox. A camera over a
worker's hands that reports their mistakes is, from that worker's perspective, a
disciplinary instrument — and systems perceived that way get unplugged. The data model is
built so the system is structurally incapable of being one.

## Data lifecycle — exhaustive

| Data | Exists where | Persisted | Retention | Leaves the host |
|---|---|---|---|---|
| Raw frames | Process memory, ring buffer | **No** (production) | `frame_buffer_seconds`, default 3 | **Never** |
| Detections / tracks | Process memory | No | Frame lifetime | Never |
| **Events** | Log | Yes | Service period + `audit_days` (7) | Only via explicit export |
| `WorldState` snapshots | Log store | Yes | Same as events | Never |
| Alerts + derivations | Log | Yes | Same as events | Only via export |
| Station / knowledge config | Disk | Yes | Until changed | Read-only inbound |
| Ticket restriction + items | Log | Yes | Service period | Never |
| Worker identity | **Nowhere** | — | — | — |
| Customer identity | **Nowhere** | — | — | — |

## Structural guarantees

1. **No worker identity exists.** The only worker field anywhere is `worker_slot: int`, a
   position at the station. No names, ids, biometrics, or per-person metrics. A future
   "which worker causes the most alerts" feature is **architecturally unavailable**, which is
   deliberate — the moment it exists, staff cooperation ends.
2. **No customer identity exists.** Tickets carry restriction + items. No name, contact,
   payment, or address. Ticket ids are opaque and rotate per service period.
3. **No pixels cross a process boundary.** Events carry zone ids, carrier ids, timestamps,
   confidences. `EvidenceRef` holds track ids and a frame *range*, never image data. Tested
   by a serialization test asserting no event type can carry a binary blob.
4. **Frame persistence is off by default**, gated behind `capture.persist_frames`, which is
   only settable in dev/eval profiles, writes to a gitignored path, and logs a loud warning
   at startup.

## A deliberate rejection: evidence video clips

Attaching a short clip to each alert would make alerts far more persuasive to a manager. It
is **rejected for MVP** because it requires persisting frames, which voids guarantee 4 and
converts the system into a recording device — the exact thing that makes staff hostile.
The **evidence trace** (`25`) is the substitute: structural rather than visual.

Recorded here rather than left implicit because this is the first feature a stakeholder will
request, and reversing it should require an ADR.

## Threat model

| Asset | Threat | MVP control | Production path |
|---|---|---|---|
| Station config / zone map | Silent tamper -> wrong allergen mapping -> silent failure | Checksum + version, `CONFIG_LOADED` in log, startup validation | Signed bundles, change approval |
| Knowledge bundle | Same — **highest-value target in the system** | Same | Same + independent review |
| Event log | Tamper to erase a hazard | Append-only in-process, gapless `seq` | Append-only store, hash chain |
| Alert channel | Suppression -> safety event | Single process, no network | Authenticated transport, heartbeat |
| Video stream | Exfiltration | Never leaves the process; no network egress path exists in code | Same, plus attestation |
| Admin/config UI | Highest-privilege surface | **Not exposed in MVP**; config is files on disk | AuthN/Z, audit trail |

**Deliberately out of scope for MVP:** authentication, multi-tenancy, TLS, RBAC, network
transport. The MVP is single-host, loopback-only, with no network egress of any media. This
is appropriate for a hackathon *and* it is the honest security posture: fewer surfaces
rather than shallow controls over many.

## The line that is never crossed

Nothing in the safety core may depend on a network. `PROTOCOL_ONLY` runs fully offline. A
system that stops protecting people when the WiFi drops is not a safety layer.


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
# FILE: docs/engineering/31-configuration.md
<!-- ==================================================================== -->

# Configuration

## Principle

Anything a restaurant, a deployment, or an experiment would legitimately change is
configuration. Anything that changes the **meaning** of a safety claim is code, reviewed,
and tested.

| In config | In code |
|---|---|
| Zone polygons, contents, kinds | Contact predicate semantics |
| Allergen taxonomy + grouping policy | Closure algorithm |
| Ingredient -> allergen maps, recipes | Grade lattice |
| All time windows (`19`) | Reset validity rules (`14`) |
| Grade thresholds per event type | Tier selection logic |
| `max_hops`, pessimistic-closure window | Pathway definition |
| Alert copy templates | Prohibited-claim lint |
| Camera/runtime parameters | Layer boundaries |

`SURFACE_WIPE` being a non-reset is **code**, not config. It is a safety semantic, and it
must not be switchable by editing a YAML file.

## Hierarchy

```
defaults.yaml  <-  profiles/<profile>.yaml  <-  station/<id>.yaml  <-  env overrides
                                                                       (dev only)
```

Later layers override earlier ones. `prod` and `demo` profiles **reject** env overrides, so
a demo cannot be accidentally running with a stray local variable.

## Validation

At startup, before entering `FULL`:
- schema validation of every layer
- referential integrity: every `zone.contents` ingredient resolves in the knowledge bundle;
  every `menu_item.required_zones` exists in the station map
- range checks on all time windows
- checksum of station + knowledge bundles

Any failure -> remain in `CALIBRATION` with a specific error. **Safety-critical config never
loads partially** (`23` P12).

## Versioning

`config_version` and `knowledge_version` are emitted in `CONFIG_LOADED` at the head of every
session log. Replay loads the versions recorded in the log, not current files — so retuning
a threshold cannot silently change what an old fixture asserts.

## Zone authoring rule (asymmetric, from `20`)

Author `INGREDIENT` zones **generously** (a false contact costs 8 seconds) and `CLEAN_STOCK`
zones **conservatively** (a false reset silently clears real taint). The asymmetry follows
from the cost structure and is easy to get backwards.


<!-- ==================================================================== -->
# FILE: docs/engineering/34-evaluation-framework.md
<!-- ==================================================================== -->

# Evaluation Framework

## The distinction that governs everything

> "The model recognized the ingredient correctly" is **not** the metric.
> "The system produced a timely, correct-tier intervention before the food could be served"
> is.

Perception metrics are diagnostic. Intervention metrics are the verdict.

## Primary metrics

### 1. Intervention Recall (IR) — the headline number
Fraction of scripted hazard scenarios in which the system produced a **correct-tier**
intervention **before** the target item reached `COMPLETE`.
`IR = correct_timely_interventions / total_hazard_scenarios`. **Target: >= 0.90 on the
scenario suite.**

### 2. Silent Miss Rate (SMR) — the number that matters most
Fraction of hazard scenarios where the system produced **no intervention** *and* asserted
the relevant carriers were `TRACKED`-clean.

This is the only genuinely bad outcome. A miss where the system had already said
"unverified" and fired Tier 0 is **not** a silent miss — declining to claim is
architecturally distinct from being wrong (`product/03`, scenario E).
**Target: 0 on the scenario suite. Any non-zero SMR blocks the phase gate.**

### 3. Nuisance Rate (NR)
Tier 1 + Tier 2 alerts per hour of normal, non-hazard preparation.
**Tier 0 is excluded by definition** — it is designed to fire liberally at ~8 seconds of
cost, and counting it as nuisance would create pressure to weaken the mechanism that carries
most of the safety value. **Target: < 1.0/hr.**

### 4. Intervention Lead Time
Seconds between alert emission and the moment the item would otherwise have been released.
Larger is better; negative is a failure regardless of correctness.
**Target: p50 > 20s, p05 > 0s.**

### 5. Tier 0 Compliance Rate
Fraction of Tier 0 prompts whose required resets were completed (observed or asserted) before
`TICKET_PREP_STARTED`. **This is the closest thing to a real-world outcome metric the system
has** — Tier 0 carries most of the safety value, and a prompt that is routinely ignored
carries none of it. **Target: > 0.80.** Falling compliance is the earliest signal that the
system has become noise.

### 6. Pessimistic Closure Rate
Fraction of Tier 0 prompts triggered **only** by `STALE`/`UNKNOWN` epistemic status rather
than by actual recorded taint. Directly instruments assumption **A6** in `PROJECT_STATE.md`,
the project's highest open risk. **Target: < 0.40.** Above that, `t_stale` is too aggressive
or camera placement is producing avoidable occlusion, and Tier 0 fatigue is imminent.

## Secondary — perception (diagnostic only)

Event-level precision/recall per event type; identity-consistency (switches per minute);
**occlusion-reporting recall** — of intervals where a carrier was truly unobservable, the
fraction perception correctly reported. *This last one is the most important perception
metric in the system*, because the safety core's conservatism depends entirely on being told
when it is blind. A pipeline with excellent detection and poor occlusion reporting is more
dangerous than the reverse.

## Secondary — reasoning

Carrier-state accuracy vs. annotated ground truth (taint set + epistemic status); pathway
reconstruction F1; tier-assignment accuracy.

## Secondary — UX and system

Time-to-comprehension and taps-to-resolve per alert tier (**target: <= 2 taps**, measured on
teammates, not self); reducer latency p99 (**< 50ms**); end-to-end contact-to-alert latency
(**< 1.5s**); frame-to-event latency; uptime in `FULL` mode.

## Benchmark sets

| Set | Contents | Used for |
|---|---|---|
| `scenarios/` A-M | Hand-authored event logs | IR, SMR, tier accuracy, determinism |
| `data/fixtures/video/` | 10-20 recorded prep sequences, annotated | Perception metrics |
| `data/fixtures/normal/` | 30+ min of ordinary prep, no hazards | Nuisance Rate |
| Adversarial | Occlusion, identity switch, camera fault | Degradation behavior |

The **normal-prep set is not optional.** Without it, every threshold optimizes toward
sensitivity, and the resulting system is the one that gets ignored in a real kitchen.

## Acceptance

A phase gate requires metrics **recorded as artifacts** in `data/eval/<date>/`, not
asserted in prose. `PROJECT_STATE.md` links the artifact that justifies each `VERIFIED`.


<!-- ==================================================================== -->
# FILE: docs/engineering/35-data-and-simulation.md
<!-- ==================================================================== -->

# Data and Simulation Strategy

Designed before model selection. The guiding question is not "how do we get a big dataset"
but "what is the smallest dataset that proves the thesis."

## What each layer needs

| Layer | Data | Volume | Source |
|---|---|---|---|
| Reasoning core | Structured event logs | ~15 fixtures | **Hand-authored.** No video required. |
| Knowledge | Taxonomy + ~25 ingredients + ~8 menu items | 1 bundle | Hand-authored |
| Zone/contact detection | Annotated overhead video | 10-20 sequences, 30-90s each | **Self-recorded** |
| Reset detection (glove change) | Annotated clips | ~40 glove-change instances | Self-recorded |
| Nuisance measurement | Normal prep, unannotated except hazard-free label | 30+ min | Self-recorded |

**The entire safety core requires zero video.** That is the point of the event-log boundary
and it is what makes P1 completable in hours.

## Annotation schema

```
VideoAnnotation {
  clip_id, station_config_version,
  events: List<{ t_ms, type, participants, zone_id?, ground_truth: true }>,
  occlusion_intervals: List<{ carrier_id, t_start, t_end }>,
  hazard_label: NONE | DIRECT | TOOL | SURFACE | BACK_CONTAMINATION
}
```

Annotation is at the **event** level, not the frame level. Frame-level labeling is an order
of magnitude more work and the contract (`21`) is defined in events, so frame labels would
not be the thing under test.

`occlusion_intervals` must be annotated even though it is tedious — it is the ground truth
for the occlusion-reporting metric (`34`), which is the perception metric that matters most.

## Simulation: what to simulate, what to record

**Simulate (hand-authored event logs):** all reasoning scenarios, temporal edge cases, hop
limits, concurrency, ambiguity, mode changes, alert storms. These are *combinatorial* and
cheap in text, expensive on video.

**Record (real video):** zone-contact geometry, occlusion realism, glove-change appearance,
lighting. These are *perceptual* and cannot be faked convincingly.

**Do not build a 3D synthetic kitchen renderer.** The sim-to-real gap for hands and
specular surfaces would consume the entire build window and produce a perception model that
works only in simulation. Recorded fixtures of the actual demo station are both cheaper and
more representative. Recorded here because "let's make a simulator" is the most seductive
wrong turn available on this project.

## Minimum viable dataset

- 13 hand-authored scenario fixtures (A-M)
- 1 knowledge bundle, 1 station config
- 12 annotated video clips covering: clean prep, direct transfer, tool transfer, surface
  transfer, back-contamination, glove change, tool swap, wipe, occlusion, identity-confusion,
  two concurrent tickets, camera obstruction
- 30 minutes of normal prep for Nuisance Rate

That is a one-afternoon recording session with a folding table and an overhead phone mount.


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

