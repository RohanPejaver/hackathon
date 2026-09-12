# Replay and Scenario Format

Source of truth for the **file format**. `product/03-scenarios.md` owns what each scenario
*means*; `/scenarios/*.yaml` own the exact sequences.

## Why replay is foundational, not a feature

Because reasoning is a pure fold (`10`), replay is not something we build — it is something
we get, provided we never break purity. It underwrites:

- deterministic tests without hardware
- exact bug reproduction (a bug report **is** a scenario file)
- comparing risk-logic changes on identical input
- a demo that can run from a recorded log if live perception degrades

Losing purity loses all four at once. This is why the clock injection rule (`19`) and the
confidence-omitting `GradedEvent` projection (`22`) are enforced from P0 rather than added
later.

## Format

```yaml
scenario: B-direct-risk-prevented
description: Station dirty from prior ticket; Tier 0 fires at bind; resets clear it.
schema_version: 1
config:
  station: fixtures/station_bagel.yaml
  knowledge: fixtures/knowledge_bagel/
  profile: eval
  overrides: { contamination.max_hops: 3 }

initial_state:
  carriers:
    gloves:   { taints: { PINE_NUT: { grade: OBSERVED, hops: 0 } }, epistemic: TRACKED }
    spreader: { taints: { PINE_NUT: { grade: OBSERVED, hops: 1 } }, epistemic: TRACKED }

events:
  - { t: 0,     type: TICKET_RECEIVED, ticket: T48, items: [turkey_sandwich],
      restrictions: [{ raw_text: "pine nut allergy" }] }
  - { t: 1000,  type: TICKET_BOUND,    ticket: T48 }
  - { t: 12000, type: GLOVE_CHANGE,    phase: DON,  worker_slot: 0, grade: OBSERVED }
  - { t: 15000, type: TOOL_SWAP,       retired: spreader, introduced: spreader_2,
      from_zone: clean_stock, grade: OBSERVED }

expect:
  - { at: 1000,  alert: { tier: 0, blocking_carriers: [gloves, spreader] } }
  - { at: 15100, alert_resolved: { tier: 0, reason: RESOLVED_BY_RESET } }
  - { no_alerts_after: 15100 }
  - { final_state: { carriers: { gloves: { taints: {} } } } }
```

`t` is milliseconds from scenario start and becomes `t_occurred`. The runner's clock is
driven entirely by these values; nothing reads a wall clock.

## Assertion vocabulary

| Assertion | Checks |
|---|---|
| `alert` | An alert with these properties exists at/after `at` |
| `alert_resolved` | Alert reaches a resolved state with the given reason |
| `no_alerts_after` | **Silence** after a timestamp |
| `no_alerts_of_tier` | Tier-specific silence |
| `final_state` | Partial match against `WorldState` |
| `state_at` | Partial match at a timestamp |
| `pathway` | A pathway with the given node sequence was found |
| `mode` | Station mode at a timestamp |
| `event_rejected` | A malformed event was quarantined, not crashed on |

`no_alerts_after` is as important as `alert`. A system that alerts on everything passes
every positive assertion.

## Determinism contract

Every fixture runs twice in CI and the outputs are diffed byte-for-byte. A fixture that is
not reproducible is a defect in the runtime, not in the fixture.

Fixtures record the `schema_version` they were authored against; forward-migrations keep old
scenarios passing across schema changes, which is what prevents the golden suite from rotting
the first time an event gains a field.

## Authoring

A fixture-authoring script in `scripts/` scaffolds a fixture from a recorded session (export event
range -> YAML). Hand-editing is expected and normal — fixtures are specification, not
generated output, and they should read like the scenario they describe.
