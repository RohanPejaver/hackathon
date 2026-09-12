# ADR-0003: No learned model between the log and an intervention

**Status:** ACCEPTED

## Context
A safety system must explain itself to a cook, a manager, and eventually an investigator.

## Alternatives
1. Learn risk end-to-end from video.
2. Learn taint propagation.
3. **Deterministic propagation and pathway search; ML confined to perception and to
   restriction normalization.**

## Decision
Option 3. Taint propagation, pathway search, and tier selection are deterministic.

## Consequences
+ Every alert is explainable as a rule chain; audit is a projection, not a research problem
+ No training data required for the part that is actually novel
- Cannot capture subtleties a learned model might; accepted deliberately

## Rationale
An unexplainable alert in this domain is an unusable alert. The pathway *is* the
explanation.
