# ADR-0001: Observation log as the architectural spine

**Status:** ACCEPTED

## Context
The system must reason about temporal sequences in a safety-critical domain, be testable
without hardware, and be debuggable after the fact. Perception is probabilistic and will
change often; safety reasoning must be stable and explainable.

## Alternatives
1. Direct pipeline — perception calls reasoning in-process with rich objects.
2. Message bus between components with independent state.
3. **Append-only event log; all downstream state is a pure fold over it.**

## Decision
Option 3. `WorldState(t) = fold(reduce, Log[0..t], Initial, Config)`. Layers 6-11 are pure
functions of the log plus versioned config.

## Consequences
+ Deterministic replay by construction; testing needs no camera
+ Evidence trace is free — every delta carries its causing event id
+ Perception and reasoning developed in parallel
+ Demo has a hardware-free fallback
- Purity must be actively defended: no wall clock (`19`), no I/O, no randomness in the core
- Some redundant recomputation; irrelevant at this scale

## Rationale
Every other desirable property of this project — testability, explainability, demo
reliability, parallel development — descends from this one decision.
