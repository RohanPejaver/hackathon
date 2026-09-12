# Observability

"Alert triggered" is not a debuggable system. The requirement is that we can always answer
**"what did the system believe, and why."**

## The evidence trace

One structure serves four purposes — debugging, evaluation, the worker/manager explanation,
and safety analysis. Because it is the *same* object that drove the decision, the
explanation cannot drift from the behavior.

```
Trace {
  alert_id, pathway_signature,
  steps: List<TraceStep>
}
TraceStep {
  event_id, t_occurred, rule_id,
  state_delta,             # exactly what changed in WorldState
  grade, narrative         # generated from a template table, not free text
}
```

Rendered form (this is literally what a manager sees on a Tier 2 hold):

```
14:31:52  ZONE_ENTRY      gloves -> bin:pesto            OBSERVED   +taint{PINE_NUT} on gloves
14:31:58  CONTACT_BEGIN   gloves <-> tool:spreader       OBSERVED   +taint{PINE_NUT} on spreader (hop 1)
14:32:19  CONTACT_BEGIN   gloves <-> bin:mayo            OBSERVED   +taint{PINE_NUT} on bin:mayo (hop 1)
          -- no GLOVE_CHANGE observed in window --
14:35:03  TICKET_BOUND    #48 restriction PINE_NUT
14:35:03  RULE precondition_unmet  -> blocking: [gloves, tool:spreader, bin:mayo]
14:35:03  ALERT tier=0    "Station not clean for PINE_NUT"
```

The absence line (`-- no GLOVE_CHANGE observed --`) is as important as the presence lines;
it is the system's actual claim (`product/01-thesis.md`).

## Log levels and their consumers

| Stream | Contents | Consumer | Retention |
|---|---|---|---|
| Event log | All committed events | Replay, evaluation, audit | audit window |
| Trace store | Derivations per alert | Manager UI, debugging | audit window |
| Metrics | Counters/histograms: event rates, late rate, occlusion duration, assertion rate, alert rate by tier, **Tier 0 compliance rate**, **pessimistic-closure rate**, reducer latency | Dev + tuning | session |
| Health | Mode changes, degradations, rejected events | Ops + demo safety | session |
| Quarantine | Schema-invalid events | Offline diagnosis | session |

**Prohibited from every stream:** image data, worker identity, customer identity.

## Inspector

A development/manager surface (separate from the worker display) showing: live carrier
states on both axes, active zones and recent contacts, bound tickets and restrictions,
active alerts with traces, mode and health, and a scrubbable event timeline.

The inspector is **read-only** and reads the same projections the runtime uses. It never
has a privileged view — if the inspector can show it, the trace can explain it.

## Replay-driven debugging

Because reasoning is a pure fold (`10`), any incident reproduces exactly: export the event
range, run `ReplayRunner`, get byte-identical state and alerts. Bug reports are therefore
**a scenario file**, not a prose description — and a fixed bug becomes a permanent
regression test automatically. This is the main practical payoff of `ADR-0001`.
