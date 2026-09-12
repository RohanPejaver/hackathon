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
