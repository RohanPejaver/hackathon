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
