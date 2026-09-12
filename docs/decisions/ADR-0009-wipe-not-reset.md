# ADR-0009: Wiping is not a valid reset

**Status:** ACCEPTED

## Context
Wiping a surface with a shared cloth redistributes protein rather than removing it.
Crediting a wipe as cleaning would let the system clear real contamination.

## Decision
`SURFACE_WIPE` is recorded (so the UI can explain why a prompt persists) and clears nothing.
Only physical replacement, or an explicit human assertion at `ASSERTED` grade, clears taint.

## Consequences
+ The system never falsely clears taint on the most common pseudo-cleaning action
- Workers who genuinely cleaned must tap "Already clean" — one tap, logged

## Rationale
The asymmetry is decisive: a missed reset costs 8 seconds; a false reset silently clears real
contamination. This is a safety semantic and therefore lives in code, not config (`31`).
