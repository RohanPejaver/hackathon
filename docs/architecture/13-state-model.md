# State Model

## Two independent axes

The most common modeling error here is collapsing "what this carrier holds" with "how much
we trust that belief." They are orthogonal and must stay that way.

```
                TAINT AXIS                          EPISTEMIC AXIS
      what allergens may be present              how trustworthy that is

   taints: Map<AllergenId, TaintRecord>        TRACKED | STALE | UNKNOWN
```

A tool that went off-camera is **not contaminated** — it is *not verifiable*. Those demand
different interventions: contamination demands a remake, non-verifiability demands eight
seconds. Collapsing them produces either dangerous optimism or unusable noise.

## Epistemic status

| Status | Meaning | Entry condition |
|---|---|---|
| `TRACKED` | Continuously observed since last state-establishing event | observation within `t_stale[kind]` |
| `STALE` | Was observed; belief has aged out | no observation for `t_stale[kind]` |
| `UNKNOWN` | Never observed, or observability broken | station start, occlusion > `t_occlusion_max`, `TRACK_IDENTITY_SUSPECT`, mode `PROTOCOL_ONLY` |

`t_stale` is per carrier kind — gloves change constantly, containers rarely move.
**Values live in `31` only**; `19` describes what the window means. Do not restate numbers
here.

### Pessimistic closure

When epistemic status is `STALE` or `UNKNOWN`, the carrier's **effective** taint set for
risk purposes becomes:

```
effective_taint(c) = c.taints                                    if TRACKED
                   = c.taints U station_recent_allergens(w)      if STALE or UNKNOWN
```

where `station_recent_allergens(w)` is the union of allergens handled anywhere at the
station within window `w` (default 30 min), each tagged grade `PESSIMISTIC`.

**The closure is never materialized in full.** It is always evaluated *against a specific
restriction's allergen set*: the question asked is "could this carrier hold anything in
`closure(R)`," never "list everything it might hold." Without this scoping a busy station
would accumulate every allergen within 30 minutes and Tier 0 would degrade to "reset
everything" — which `18` identifies as the failure that makes workers ignore the prompt.
Combined with recipe-scoped required carriers (`15`), a Tier 0 prompt names two or three
specific items, not the whole station.

This is the mechanism that makes occlusion safe. It looks aggressive, and it would be — if
it drove Tier 1. It does not: `PESSIMISTIC` grade can only ever produce **Tier 0**
(`15`). The blast radius is contained by the tier design, so the conservative closure costs
eight seconds, not a remake.

## Reducer

```
reduce : (WorldState, GradedEvent, Config) -> (WorldState, List<StateDelta>)
```

Pure. Total. No I/O, no clock access, no randomness. Time comes only from
`event.t_occurred`. Every mutation emits a `StateDelta` carrying the causing `event_id` —
this is what makes the evidence trace free rather than a separate logging concern.

### Transition table

| Event | Effect |
|---|---|
| `ZONE_ENTRY(c, z)` where `z.kind == INGREDIENT` | `c.taints ∪= allergens(z.contents)`, grade = event grade, `hops = 0` |
| `CONTACT_BEGIN(a, b)` | **bidirectional**: `a.taints ∪= b.taints`, `b.taints ∪= a.taints`, each with `hops+1`, propagation halts at `max_hops` |
| `GLOVE_CHANGE(phase=DON)` | `gloves.taints = {}`, epistemic = `TRACKED` |
| `TOOL_SWAP` / `SURFACE_SWAP` | retired carrier leaves the active set; introduced carrier inherits `CLEAN_STOCK` state |
| `WASH_CYCLE(c)` | `c.taints = {}` at grade `ASSERTED`; epistemic unchanged |
| `OPERATOR_ASSERTION(c, CLEAN)` | `c.taints = {}` at grade `ASSERTED`; `asserted_at` recorded |
| `SURFACE_WIPE` | **no taint change.** Records `last_wiped_at` for UI explanation only |
| `CARRIER_OBSERVABILITY_CHANGED` | epistemic transition only |
| `TRACK_IDENTITY_SUSPECT(c1, c2)` | `c1.taints = c2.taints = c1.taints ∪ c2.taints`; both -> `STALE` |
| `STATION_MODE_CHANGED(PROTOCOL_ONLY)` | all carriers -> `UNKNOWN` |

### Why propagation is bidirectional

A tainted hand entering the mayo tub contaminates the tub; a hand entering an already-
contaminated tub becomes contaminated. Contact is physically symmetric, and asymmetric
modeling would silently miss exactly the back-contamination case that is the product's
signature capability (`product/01-thesis.md`). Cost: slightly more conservative. Accepted.

## Grade lattice

```
OBSERVED  >  INFERRED  >  ASSERTED  >  PESSIMISTIC
```

Rules:
- Propagation takes the **minimum** of the source taint's grade and the event's grade.
  Evidence never strengthens by being passed along.
- A grade is **never silently upgraded**. An `ASSERTED`-clean carrier does not become
  `OBSERVED`-clean until independently observed.
- Grade determines the maximum tier reachable: `OBSERVED` -> Tier 2; `INFERRED`/`ASSERTED`
  -> Tier 1; `PESSIMISTIC` -> Tier 0 only.

## Expiry

Taint does **not** decay with time. There is no half-life for allergenic protein, and a
time-based decay would be the system quietly inventing a safety claim it cannot support.
Taint is removed only by a valid reset or by the carrier leaving the active set. What *does*
age is the epistemic axis.

## Snapshots — deferred

A snapshot mechanism would speed up replay of long logs. **Do not build it until replay is
measurably slow.** At station scale a full fold is milliseconds, and a snapshot that drifts
from the fold is a correctness hazard for no current benefit. If built: a snapshot is never
authoritative and must be byte-reproducible by folding from zero, with a test asserting it.
