# ADR-0006: Ticket-to-station binding is an explicit human action

**Status:** ACCEPTED

## Context
The system must know which ticket is being prepared. Two sandwiches on one board are
visually identical.

## Alternatives
1. Infer from vision.
2. Infer from timing heuristics.
3. **One tap on the station display (already an existing KDS gesture).**

## Decision
Option 3. `TICKET_BOUND` is only ever operator-sourced.

## Consequences
+ Removes an entire class of unbounded downstream error
+ Every guarantee downstream stops inheriting a vision error rate
- ~1 second of human effort per ticket

## Rationale
A deliberate trade of one second for the elimination of a failure mode we cannot bound.
Documented explicitly because it otherwise looks like a shortcut and will be "fixed."
