# Contamination Model

## What "cross-contamination risk" means computationally

Not `allergen_detected == true`. A **transfer pathway**:

> Given allergen source `A` and target food `F`, a pathway exists iff there is a sequence of
> carriers `A -> c1 -> c2 -> ... -> F` such that:
> 1. each step is a contact event in the log,
> 2. the steps are **strictly ordered in time** (`t(e_i) < t(e_{i+1})`),
> 3. **no valid reset** occurred on `c_i` between its inbound and outbound contact,
> 4. path length <= `max_hops`.

The pathway *is* the evidence trace. The same structure that determines risk is the one
shown to the worker — no separate explanation layer, and therefore no possibility of the
explanation drifting from the decision.

## Pathway classes

| Class | Shape | Example |
|---|---|---|
| **Direct** | `source -> target` | hand from pesto bin straight onto the bagel |
| **Tool-mediated** | `source -> tool -> target` | spreader used for pesto then for the order |
| **Surface-mediated** | `source -> hands -> surface -> target` | scenario C |
| **Back-contamination** | `source -> hands -> container` | pesto into the shared mayo tub. **Target is a future ticket, not the current one.** |
| **Re-entry** | `source -> c -> ... -> c` | repeated use of the same tool; one episode, not N |

Back-contamination is structurally different and must not be special-cased: it is an
ordinary pathway whose terminal node is a `CONTAINER`, which then becomes a *source* for
all subsequent pathways. It falls out of the model for free — which is the argument that
the model is the right one.

## Reset semantics

**Valid resets** (clear taint):

| Reset | Grade | Why valid |
|---|---|---|
| `GLOVE_CHANGE(DON)` | `OBSERVED` | Physical replacement, visually verifiable |
| `TOOL_SWAP` | `OBSERVED` | Identity change; new carrier from clean stock |
| `SURFACE_SWAP` | `OBSERVED` | As above |
| `WASH_CYCLE` | `ASSERTED` | We see it went to the sink; efficacy is unobservable |
| `OPERATOR_ASSERTION` | `ASSERTED` | A human vouched; logged, never promoted |

**Explicitly not a reset:**

- `SURFACE_WIPE`. A shared wipe cloth redistributes protein rather than removing it. The
  system records the wipe (so the UI can explain *why* the prompt is still up) and clears
  nothing. Scenario J is the regression test.
- Rinsing, time elapsed, "it looks clean," a new ticket starting.

**Rag modeling (documented, deliberately not implemented):** a wipe cloth is a `TOOL`-kind
carrier and should propagate taint surface->rag->surface. The domain model and event schema
support this today. MVP perception does not detect rags, so no `CONTACT` events involving
one are produced. This is a *known, bounded* gap, recorded here so nobody assumes coverage.

## Evidence sufficiency

| Determination | Requires |
|---|---|
| **Potential contamination** | >=1 pathway, all edges `OBSERVED`, no reset on any node, hops <= `max_hops` |
| **Risk mitigated** | A valid reset on any node of every known pathway, at grade >= the pathway's grade |
| **Insufficient evidence** | Any node `STALE`/`UNKNOWN`, or any edge below `OBSERVED`, or a pathway broken only by `PESSIMISTIC` reasoning |

"Insufficient evidence" is a **first-class outcome**, not a failure. It maps to Tier 0, and
it is the correct answer far more often than either of the other two.

## Parameters (config, `31`)

| Key | Default | Rationale |
|---|---|---|
| `contamination.max_hops` | `3` | Beyond three transfers, transferred protein is negligible and paths become noise. Tunable per restaurant. |
| `contamination.strength_decay_per_hop` | `PRESENT -> PRESENT -> POSSIBLE` | `may_contain` sources start at `POSSIBLE` and never rise. |
| `contamination.station_recent_window` | `30m` | Window for pessimistic closure (`13`). |

`max_hops` is an **assumption, not a fact.** It is not empirically grounded and is recorded
as an open question in `experiments/README.md`. It is configuration precisely so that being
wrong about it is a config change, not a rewrite.
