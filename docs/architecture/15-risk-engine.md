# Risk Engine

Operates **only** on structured state. It has no knowledge of cameras, frames, models, or
confidence floats. It is a pure function and is fully testable from hand-authored input.

```
assess : (WorldState, List<Ticket>, Knowledge, Config) -> List<RiskAssessment>
```

## Two algorithms, two tiers

A deliberate asymmetry: the tiers have different evidence requirements, so they use
different computations. Trying to serve both with one algorithm is what makes naive
versions of this system either noisy or blind.

### 1. Precondition check -> Tier 0 (cheap, runs at bind)

At `TICKET_BOUND`, for a ticket with restriction `R`:

```
required_zones  = recipe_zones(ticket.items)              # from knowledge
required_carriers = carriers_for(required_zones) U {GLOVES}
for c in required_carriers:
    if effective_taint(c) ∩ closure(R.allergen_ids) != {}:  -> reset required
    if c.epistemic != TRACKED:                              -> reset required
```

No graph search. No pathway. **No evidence requirement at all** — uncertainty alone is
sufficient, because the remedy costs eight seconds. Output is the explicit list of carriers
needing reset, which becomes the worker's checklist.

### 2. Pathway search -> Tier 1 / Tier 2 (expensive, runs on contact)

Bounded backward search from the target food carrier over the temporal contact graph,
per `14`. Complexity is bounded by `max_hops` and the active carrier set (typically < 10
carriers), so this is trivially real-time; no optimization is warranted and none should be
added speculatively.

Returns `List<Pathway>`, each with: node sequence, edge event ids, minimum grade along the
path, hop count, and whether any node carries a reset that breaks it.

## Allergen matching

Matching uses the **transitive closure over the taxonomy graph** (`18`), not string
equality:

```
closure(PINE_NUT) may include TREE_NUT depending on restaurant taxonomy config
```

The taxonomy is data, configured per restaurant, defaulting to the conservative (broader)
grouping. Whether pine nut should group under tree nut is a **domain policy question, not a
code question** — botanically it is a seed, but many operators group it. Encoding it in
code would make a restaurant-specific policy a source change.

## Output

```
RiskAssessment
  ticket_id, allergen_id
  level: CLEAR | UNVERIFIED | PATHWAY_OPEN | PATHWAY_RESOLVED
  pathways: List<Pathway>
  blocking_carriers: List<CarrierId>     # for UNVERIFIED: what needs reset
  max_grade: EvidenceGrade
  assessed_at, config_version, knowledge_version
```

| Level | Meaning | Drives |
|---|---|---|
| `CLEAR` | No pathway; all required carriers `TRACKED` and free of matching taint | nothing |
| `UNVERIFIED` | No observed pathway, but preconditions unmet or state not verifiable | **Tier 0** |
| `PATHWAY_OPEN` | >=1 unbroken `OBSERVED` pathway into the target | **Tier 1** (in prep) / **Tier 2** (complete) |
| `PATHWAY_RESOLVED` | Every pathway broken by a valid reset, or asserted by a human | resolves an open alert |

There is deliberately **no `SAFE` value.** `CLEAR` means "no pathway found under current
evidence," which is a statement about the system's knowledge, not about the food.
`product/02-safety-boundaries.md` makes this a tested prohibition.

## Tier selection

```
level == UNVERIFIED                                  -> Tier 0
level == PATHWAY_OPEN and max_grade == OBSERVED
    and ticket.lifecycle == IN_PREP                  -> Tier 1
level == PATHWAY_OPEN and ticket.lifecycle == COMPLETE-> Tier 2
level == PATHWAY_OPEN and max_grade <  OBSERVED      -> Tier 0   (downgrade, never up)
level == CLEAR | PATHWAY_RESOLVED                    -> none
```

The penultimate rule is the system's core epistemic commitment in one line: **weak evidence
downgrades the intervention, it never lowers the bar for a strong one** (`ADR-0005`).

## Where ML does and does not belong

| Component | Approach | Why |
|---|---|---|
| Detection / tracking | Learned | Genuinely a perception problem |
| Action segmentation (dwell, episode boundaries) | Deterministic thresholds first | Must be tunable and explainable; revisit only with evidence |
| Contact predicate | Deterministic geometry | Auditable, testable, no training data required |
| Taint propagation | **Deterministic** | A learned propagation model would be unexplainable and unauditable in a safety context |
| Pathway search | **Deterministic** | ditto |
| Tier selection | **Deterministic** | ditto |
| Restriction normalization (free text -> allergens) | Learned/assisted, with mandatory `AMBIGUOUS` fallback | Language is genuinely open-set; but it may never guess |

**No machine-learned model may sit between the event log and an intervention.** That is the
architectural line (`ADR-0003`). The safety core is explainable end to end or the product's
central claim is false.
