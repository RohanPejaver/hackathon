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
