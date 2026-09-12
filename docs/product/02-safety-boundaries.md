# Safety Boundaries

These are **behavioral requirements encoded in the system**, not disclaimers. Each is
traceable to an architectural mechanism and a test.

## Supported claims

The system may state, and the architecture must be able to substantiate:

| Claim | Mechanism | Test level |
|---|---|---|
| "A hand entered the pesto zone at T" | Contact event, `OBSERVED` grade | perception + replay |
| "No glove change was observed between T1 and T2" | Absence of `RESET` event in window | replay |
| "This tool has an unbroken contact path from an allergen source" | Pathway search (`15`) | risk-engine |
| "This station's state is not currently verifiable" | Epistemic status `UNKNOWN`/`STALE` (`13`) | replay |
| "This ticket's restriction could not be resolved" | `Restriction.resolution = AMBIGUOUS` (`17`) | order-model |

## Unsupported claims — architecturally prohibited

The system must be **structurally incapable** of producing these, not merely discouraged:

| Prohibited claim | Enforcement |
|---|---|
| "This food is allergen-free / safe" | No `SAFE` value exists in any risk enum. `RiskLevel` has no positive-safety member. |
| "Contamination occurred" | `RiskLevel` names *pathway* states, never physical outcomes. UI copy lint forbids the word in alert templates. |
| "This surface is clean because it was wiped" | `SURFACE_WIPE` is recorded but is not in the valid-reset set (`14`). Unit-tested. |
| "Cleaning was effective" | Wash-cycle resets carry grade `ASSERTED`, never `OBSERVED`. |
| Any statement about a named worker | No identity fields exist on the worker entity (`11`, `24`). |

## Human responsibility

The human is the decision-maker at every tier. The system:

- **proposes** remediation; it never performs one
- **holds** an item; it never releases one — only a human clears a Tier 2 hold
- **records** a human assertion as `ASSERTED` grade and never silently promotes it to `OBSERVED`
- **cannot** cancel, refund, or communicate with a customer

## Fail-safe behavior

The governing rule: **degraded perception must increase conservatism and decrease cost, never the reverse.**

| Condition | Behavior |
|---|---|
| Carrier not observed recently | Epistemic status degrades -> pessimistic closure -> Tier 0 at next bind |
| Camera fault / total vision loss | Station enters `PROTOCOL_ONLY` mode: Tier 0 still fires on every restricted ticket, UI states vision is unavailable. **The product retains its primary value with zero perception.** |
| Tracker identity ambiguity | Confusable carriers' taint sets are **merged** (pessimistic), both marked `STALE`. Never silently reassigned. |
| Reasoning core exception | Station enters `PROTOCOL_ONLY`, existing Tier 2 holds persist, incident logged. Never fail-open to silence. |
| Ticket restriction ambiguous | Binding is **blocked**. The system asks; it does not guess. |

## The one rule that subsumes the rest

> Low confidence must trigger a **human-verification workflow at the cheapest tier**, never a
> lowered alert threshold at a high tier.

Lowering thresholds under uncertainty makes the system noisiest exactly when it is least
trustworthy, which is the mechanism by which safety systems get ignored. See
`decisions/ADR-0005`.
