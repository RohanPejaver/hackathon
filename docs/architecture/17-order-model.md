# Order / Ticket Model

## Abstract source

No third-party platform appears anywhere in the core. The boundary is:

```
OrderSource (interface, see `22`)
  poll() -> List<RawOrder>
  RawOrder: { external_id, items: List<str>, notes: List<str>, received_at }
```

MVP implementations: `ManualEntrySource` (a cashier types it) and `FixtureSource` (replay).
Any POS/delivery adapter is an implementation of this interface and lives in an adapter
module, never in `orders/` core. Delivery-platform integration is explicitly **deferred**
(`engineering/38-workflow.md` priorities) — free-text allergy notes are a normalization
problem, not an integration problem, and the normalizer is where the value is.

## Restriction normalization

```
normalize : (raw_text, Knowledge) -> Restriction
```

Three outcomes, and the third is the important one:

| Outcome | Condition | Effect |
|---|---|---|
| `RESOLVED` | Text maps to >=1 known allergen with high confidence | `allergen_ids` populated; ticket may bind |
| `AMBIGUOUS` | Allergy intent detected, specific allergen not determinable ("ALLERGY", "no nuts?") | **Binding blocked.** Resolution request routed to front-of-house. |
| `UNRESOLVABLE` | Names something outside the knowledge base | Binding blocked; escalated to a manager |

**The normalizer may never guess.** Low confidence produces `AMBIGUOUS`, never a
best-effort allergen. Enforced by a test asserting that below-threshold inputs never yield
`RESOLVED` (scenario G).

Normalization output is **cached on the ticket**, not recomputed, so that a re-run of the
normalizer (a model change) cannot silently alter an in-flight ticket's meaning.

## Ticket lifecycle

```
RECEIVED ──normalize──┬─ RESOLVED ──> (bindable)
                      └─ AMBIGUOUS/UNRESOLVABLE ──> BLOCKED ──resolve──> RECEIVED
(bindable) ──tap──> BOUND ──> IN_PREP ──> COMPLETE ──┬──> RELEASED
                                                      └──> HELD ──human──> RELEASED | VOIDED
any ──> VOIDED (timeout `t_abandon` = 15m, or explicit)
VOIDED/RELEASED ──rework──> new Ticket{rework_of: id}
```

Invariants (tested):
1. `BLOCKED` -> `BOUND` is unreachable.
2. `HELD` -> `RELEASED` requires an operator event; no timer, no system path.
3. A `VOIDED` ticket contributes no risk assessments but its events remain in the log.

## Binding — explicit, never inferred

`TICKET_BOUND` is produced by a **human action** (one tap on the station display), never by
vision. Inferring which ticket a cook is currently preparing from pixels is not reliably
solvable and every downstream guarantee would inherit its error rate.

This is a deliberate trade of one second of human effort for the removal of an entire class
of unbounded failure (`ADR-0006`). It is not a shortcut, and the doc says so because it will
otherwise be "fixed" by a future contributor.

## Concurrency

The station holds a **set** of bound tickets. Because taint lives on carriers and never on
tickets (`11`), no contact attribution is required and concurrency needs no special
handling in the state or risk layers.

The one concurrency rule that does exist is a protocol rule, not a technical one:

> `>= 2` bound tickets with non-empty restrictions raises station condition
> `MULTI_RESTRICTION` -> Tier 0 escalation: *"Two active restrictions — sequence them."*

This mirrors standard kitchen allergen protocol (prep restricted orders separately). The
system enforces the existing rule rather than inventing one it cannot substantiate
(scenario F).

## Substitutions and rework

A substitution changes `items`, therefore `required_zones`, therefore Tier 0 preconditions.
It emits `TICKET_ITEM_SUBSTITUTED` and triggers reassessment. A rework opens a **new**
ticket referencing the original; state is never mutated backwards, preserving log
append-only semantics.
