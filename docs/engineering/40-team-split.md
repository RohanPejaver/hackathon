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
