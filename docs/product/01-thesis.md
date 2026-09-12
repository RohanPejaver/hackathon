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
