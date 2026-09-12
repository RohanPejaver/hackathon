# Dependency Policy

Technology follows architecture. No dependency is selected because it is popular.

## Principles

1. **`domain/`, `events/`, `state/`, `risk/`, `policy/` have zero heavy dependencies.**
   The safety core must be runnable, testable, and reviewable without vision or ML installed.
   This is the practical test of `ADR-0001`: if running the risk tests requires a GPU, the
   boundary has already leaked.
2. **ML/vision dependencies are optional extras**, installed only for the `perception` and
   `eval` groups. `pip install` of the core must not pull a deep-learning runtime.
3. **Pin exactly** for anything affecting numerical output. Determinism outranks freshness.
4. **Licensing:** permissive only (MIT/BSD/Apache-2.0) for anything linked into the runtime.
   Copyleft or research-only-licensed model weights are disqualifying, since the demo is
   presented publicly.
5. **Prefer stdlib** for serialization, hashing, and time. These sit on the determinism path.
6. **One dependency per job.** Two libraries that overlap is a decision to be made, not
   deferred.
7. A dependency that would encode domain semantics (an off-the-shelf "allergen database"
   package) is rejected — that knowledge is restaurant-scoped config (`18`).

## Selection gate

Before adding any dependency, record in the PR description: what it does, what it replaces,
its license, whether it is on the determinism path, and which dependency group it belongs to.
Anything in the core group additionally requires an ADR.

## Reproducibility

Lockfile committed. Model weights (when introduced) are versioned artifacts with recorded
checksums, referenced by version in config, never vendored into git.
