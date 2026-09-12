# ADR-0008: Taint is carried by carriers, never by dishes or tickets

**Status:** ACCEPTED

## Context
Multiple concurrent tickets make "which contact belongs to which order" unanswerable from
observation.

## Decision
Contamination attaches to gloves, tools, surfaces, and containers. Tickets supply only a
restriction filter, a time window, and an expected zone set.

## Consequences
+ Concurrency requires no attribution logic at all (scenario F)
+ Back-contamination of shared containers falls out for free — it is an ordinary pathway
  whose terminus is a container
- Slightly less specific alerts ("this tool is implicated" rather than "this sandwich is")

## Rationale
This is the core modeling insight of the product. Attributing taint to dishes would require
solving a problem that has no reliable solution.
