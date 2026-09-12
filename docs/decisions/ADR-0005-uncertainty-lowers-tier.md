# ADR-0005: Low confidence lowers the tier, never the bar

**Status:** ACCEPTED

## Context
Section 14 of the planning brief asked directly: should low confidence lower the alert
threshold, or trigger human verification?

## Decision
**Human verification at the cheapest tier.** Weak evidence downgrades an intervention
(toward Tier 0, ~8 seconds) and never permits a high-cost intervention on weak grounds.
Encoded in tier selection (`15`) and in the grade->max-tier mapping (`13`).

## Consequences
+ The system is noisiest where it is cheapest and quietest where it is least sure
+ Tier 1/2 remain credible because they always mean observed evidence
- More Tier 0 prompts; acceptable by design

## Rationale
Lowering thresholds under uncertainty makes a system loudest exactly when least trustworthy.
That is the mechanism by which safety systems get ignored, and being ignored is the only
failure mode from which there is no recovery.
