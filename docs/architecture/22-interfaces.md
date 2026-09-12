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
