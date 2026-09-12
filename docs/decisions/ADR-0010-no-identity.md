# ADR-0010: No worker or customer identity in the data model

**Status:** ACCEPTED

## Context
A camera over a worker that reports their mistakes is a disciplinary instrument, and systems
perceived that way are defeated by the people they monitor. Customer PII adds regulatory
surface for no functional gain.

## Decision
The only worker field anywhere is `worker_slot: int` (a position). Tickets carry restriction
and items only. No names, ids, biometrics, faces, or per-person metrics anywhere in
`domain/`.

## Consequences
+ A "which worker causes the most alerts" feature is architecturally unavailable — deliberate
+ Sharply reduced privacy and regulatory surface
- Cannot do per-person training analytics; accepted, and in fact desired

## Rationale
Adoption is the binding constraint on a system like this, and it is decided by whether staff
believe the camera is for them or against them.
