# CLAUDE.md — Project Root

Allergen cross-contamination safety layer for a food-prep workstation.
See `docs/product/01-thesis.md` for what this is.

> **Engineering conduct is governed by `docs/CLAUDE.md`** (pre-existing, authoritative:
> think before coding, simplicity first, surgical changes, goal-driven execution). This file
> adds *project* context only and does not restate it.
>
> This root file exists because `docs/CLAUDE.md` is only reliably loaded while working inside
> `docs/`, and its rules must apply to `src/` work too.

## Operating procedure

**Every session, before acting:**
1. `docs/PROJECT_STATE.md` — status, next action, unresolved assumptions
2. `docs/README.md` — the index and the source-of-truth table
3. The architecture doc owning the subsystem you are touching

**Before writing any code:** `docs/architecture/22-interfaces.md` (the only home for
signatures) and `docs/engineering/33-testing-strategy.md`.

**At the end of a session:** update `docs/PROJECT_STATE.md` §2, §3, §5, §8.

## Rules specific to this project

1. **Never let perception import safety.** `state/`, `risk/`, `policy/`, `orders/` may not
   import `perception/`. CI enforces it; do not work around it.
2. **The reasoning core is pure.** No wall clock, no I/O, no randomness in
   `state/`/`risk/`/`policy/`. Time comes from `event.t_occurred`. This is what makes replay
   deterministic — see `ADR-0001`.
3. **Never branch on `confidence`.** Branch on `grade`. See `ADR-0004`.
4. **The system never claims food is safe or contaminated.** It reports what was observed and
   not observed. See `docs/product/02-safety-boundaries.md`.
5. **A bug report is a scenario file.** Reproduce in `/scenarios/`, then fix. The fixture
   becomes a permanent regression test.
6. **Code existing is not "done."** A phase is `VERIFIED` only with the evidence artifact
   named in `docs/engineering/38-workflow.md`.
7. **Build the reasoning core before perception.** P1 needs no camera and is the part that is
   actually novel.

## When docs and code disagree

That is a defect, not a doc edit. Decide which is wrong first. Precedence:
`docs/CLAUDE.md` > ADRs > `docs/product/` > `docs/architecture/` > `docs/engineering/` >
code comments.
