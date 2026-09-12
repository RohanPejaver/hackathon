# Alert Model

## Alert identity — the anti-spam mechanism

```
pathway_signature = hash(ticket_id, allergen_id, root_source_carrier, ordered_node_ids)
alert_key         = (station_id, pathway_signature)
```

Two observations are **the same alert** iff they share an `alert_key`. Ten seconds of
continuous contact with one tainted spreader yields one pathway, one signature, one alert —
updated, not re-raised.

Suppression happens at **three** layers, each solving a different duplication:

| Layer | Mechanism | Solves |
|---|---|---|
| Assembly (`12`) | Contact **episodes** (`BEGIN`..`END`) with dwell + hysteresis | 30fps -> 1 event |
| Policy (this doc) | `alert_key` dedup | Same hazard re-derived on each tick |
| Presentation (`H`) | One visible alert per station, highest tier wins | Visual overload |

Solving it only at the UI layer would leave the log full of noise and poison the evaluation
metrics; solving it only at assembly would still re-raise on every reassessment. All three
are required.

## Lifecycle

```
RAISED ──ack──> ACKNOWLEDGED ──┐
   │                            ├──> RESOLVED_BY_RESET      (a valid reset broke every pathway)
   │                            ├──> RESOLVED_BY_ASSERTION  (human vouched; ASSERTED grade)
   ├──escalate──> ESCALATED ────┤
   │                            └──> RESOLVED_BY_REMAKE     (item voided / reworked)
   └──expire──> EXPIRED         (Tier 0 only, on ticket void)
```

Rules:

- **Tier 2 has no expiry and no auto-resolution.** Only an explicit human action clears a
  hold. The system never releases its own hold (`product/02`).
- Tier 0 auto-resolves the instant its preconditions are met — the checklist items tick
  themselves off as resets are observed. This is deliberate: compliance should feel like
  progress, not paperwork.
- Tier 1 auto-resolves on a pathway-breaking reset, and the UI *shows* the resolution rather
  than silently clearing it, so the worker learns the causal link.

## Escalation

| From | Condition | To |
|---|---|---|
| Tier 0 | Ticket reaches `IN_PREP` with preconditions still unmet | Tier 1 |
| Tier 1 | Unacknowledged for `t_escalate` (default 20s) **and** ticket reaches `COMPLETE` | Tier 2 |
| Tier 2 | Unresolved for `t_manager` (default 60s) | Manager surface (deferred post-MVP) |

Escalation is time-and-lifecycle driven, never severity-inflation driven. An alert never
escalates merely because it has been repeated.

## Cooldown

After `RESOLVED_BY_ASSERTION`, the same `alert_key` is suppressed for `t_cooldown`
(default 120s) to prevent immediately re-alerting on the same human-vouched carrier. The
suppression is **logged as a suppression event** so evaluation can distinguish "did not
fire" from "fired and was suppressed" — without that distinction the nuisance-rate metric is
meaningless.

## Alert payload

```
Alert
  alert_id, alert_key, pathway_signature
  tier: 0 | 1 | 2
  ticket_id, allergen_id
  headline        : str         # <= 6 words, read at a glance
  required_actions: List<Action># e.g. [NEW_GLOVES, SWAP_TOOL(spreader)]
  derivation      : List<(event_id, rule_id, state_delta)>   # the evidence trace
  raised_at, state, acknowledged_by_slot?
```

`headline` and `required_actions` are what the worker sees. `derivation` is what a manager
or engineer inspects. Both come from the same object, so they cannot disagree — a UI copy
lint test asserts `headline` never contains a prohibited claim word (`02`).
