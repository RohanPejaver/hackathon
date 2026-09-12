# ADR-0004: Confidence is thresholded into a grade at the boundary

**Status:** ACCEPTED

## Context
Continuous confidence propagating through state makes behavior untestable, unexplainable,
and impossible to reason about in aggregate.

## Alternatives
1. Probabilistic state (taint as a distribution).
2. **Threshold at the event boundary into `EvidenceGrade`; discrete state thereafter.**

## Decision
Option 2. `confidence` remains on the event as metadata for evaluation and tuning. The
reducer receives a `GradedEvent` projection that **omits the float**, so the type system
enforces this rather than reviewer discipline. A test asserts reducer output is invariant to
`confidence`.

## Consequences
+ State is inspectable and assertable in fixtures
+ Uncertainty is handled at the policy layer, which knows the cost of each action
- Information is lost at the threshold; mitigated by keeping the float for offline tuning

## Rationale
"Knife is 0.63 contaminated" is neither actionable nor auditable. Grades are.
