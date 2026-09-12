# Testing Strategy

Written before implementation, deliberately. The test hierarchy is what allows the safety
core to be finished and verified before a camera exists.

## Levels — and what each *proves*

| Level | Input | Proves | Gate for |
|---|---|---|---|
| **Unit** | Functions | Component correctness | every phase |
| **Property** | Generated event sequences | Invariants from `11` hold universally: determinism; taint monotonic between resets; every taint has a source event; `hops` strictly increases; reducer output invariant to `confidence` | P1 |
| **Domain** | Taxonomy + ingredient fixtures | Closure and resolution correctness, incl. `may_contain` strength | P2 |
| **State transition** | Hand-built event sequences | Every row of the `13` transition table, **including the ones that must do nothing** (`SURFACE_WIPE`) | P1 |
| **Risk engine** | Hand-built `WorldState` + tickets | Pathway search: direct, tool, surface, back-contamination, hop limit, reset-breaks-path, temporal ordering | P1 |
| **Policy** | `RiskAssessment` sequences | Tier selection, `alert_key` dedup, escalation timing, cooldown, suppression logging | P1 |
| **Replay / scenario** | `/scenarios/*.yaml` | **End-to-end reasoning with zero perception.** All of A-M. The backbone. | P1, P3 |
| **Perception** | Annotated video fixtures | Event-level precision/recall per event type; occlusion reporting honesty | P4, P5 |
| **Integration** | Recorded video + fixture tickets | Camera -> events -> alert, wired | P4 |
| **End-to-end** | Live station | The demo path | P6 |
| **Adversarial** | Scenarios K-M + fuzzed logs | Identity switch, camera fault, alert storms, malformed events | P4+ |

## The replay suite is the backbone

Every product scenario (`product/03-scenarios.md`) is an executable fixture. Every bug
becomes a fixture. Every failure mode in `23` maps to a fixture or an offline metric, and a
meta-test asserts that mapping is **total** — a failure mode with no test is a tracked
defect, not an oversight.

## Required negative tests

Easy to forget, and each guards a claim the product makes:

- Scenario A asserts **silence** — no alert, no prompt.
- `SURFACE_WIPE` asserts **no state change**.
- Below-threshold normalizer input asserts **never** `RESOLVED`.
- `BLOCKED -> BOUND` asserts **unreachable**.
- Alert copy lint asserts prohibited claim words never appear in any template (`02`).
- Serialization asserts **no event type can carry binary data** (`24`).
- Determinism asserts every fixture run twice produces byte-identical output.

## What is deliberately not tested

Cleaning efficacy, food identity, and anything requiring ground truth about actual protein
transfer. These are outside the system's claims (`02`); tests asserting them would imply
capabilities the product denies having.
