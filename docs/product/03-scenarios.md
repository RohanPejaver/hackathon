# Canonical Scenarios (A-H)

These eight scenarios are the **behavioral contract** of the system. Each has a
corresponding executable replay fixture in `/scenarios/`, and each is a required gate for
Phase P1 (see `engineering/38-workflow.md`).

This document is the source of truth for *what each scenario means*.
`engineering/36-replay-and-scenarios.md` is the source of truth for the *file format*.
The `/scenarios/*.yaml` files are the source of truth for the *exact event sequences*.

Station used throughout: bins `pesto`, `mayo`, `turkey`, `bread`; carriers `gloves`,
`spreader`, `board`, `landing`. Restriction throughout: `PINE_NUT`.

---

## A — No risk

Ticket has no restriction, or a restriction with no intersection against the station map.

**Expected:** complete silence. No Tier 0. No alert. Carrier state updates normally.
**Proves:** the system is quiet by default. *A scenario that asserts the absence of output is
as important as one that asserts presence.*

## B — Direct risk, prevented

Gloves and spreader carry `OBSERVED` taint `{PINE_NUT}` from a prior ticket. A `PINE_NUT`
ticket binds.

**Expected:** Tier 0 fires **at bind, before any motion**, listing exactly the carriers
requiring reset. On observing `GLOVE_CHANGE` + `TOOL_SWAP`, carriers reset to
`OBSERVED`-clean, prompt clears, prep proceeds silently.
**Proves:** the primary value path — contamination is *prevented*, not merely detected.

## C — Indirect risk (multi-hop)

`gloves -> pesto`, then `gloves -> board`, then clean bread placed on `board`, then bread
enters the restricted item. No reset anywhere.

**Expected:** pathway of length 3 found; Tier 1 during prep, escalating to Tier 2 if the
item completes unresolved.
**Proves:** transitive propagation through surfaces; the pathway search is not a
first-order adjacency check.

## D — False positive (worker actually cleaned)

System believes `spreader` is tainted; the swap happened off-camera.

**Expected:** prompt reads *"Spreader last observed contacting pesto. Replacement not
observed."* Worker taps **"Already swapped"** -> `OPERATOR_ASSERTION` event -> carrier
becomes `ASSERTED`-clean -> prompt clears. One tap. No remake. No argument.
**Proves:** the epistemic framing converts what would be a dispute into a one-tap
resolution, and human corrections are first-class events in the same log.

## E — False negative (unobserved transfer)

A real transfer occurs entirely outside the contact model (e.g. a splash, an unmodeled
carrier).

**Expected:** the system produces **no** Tier 1/2 alert — and this is not scored as a
silent failure *provided* the relevant carriers were reported `STALE`/`UNKNOWN` and Tier 0
fired at bind. A **Silent Miss** is only recorded when the system asserted `TRACKED`-clean
and was wrong.
**Proves:** declining to claim is architecturally distinct from missing. See
`engineering/34-evaluation-framework.md`.

## F — Concurrent restricted orders

Two tickets with different restrictions bound to one station simultaneously.

**Expected:** no per-ticket attribution is attempted. Station raises condition
`MULTI_RESTRICTION` -> Tier 0 escalation: *"Two active restrictions — sequence them."*
**Proves:** carrier-held taint makes concurrency a non-problem, and the system enforces
existing kitchen protocol rather than inventing one it cannot support.

## G — Ambiguous restriction

Ticket free-text reads `"ALLERGY"` with no allergen named.

**Expected:** `Restriction.resolution = AMBIGUOUS`. **Binding is blocked.** A resolution
request is routed to front-of-house. No prep may start. The system never guesses.
**Proves:** bad input is surfaced *before* food is made, not after.

## H — Out of view

Hands leave the station frame for longer than `t_stale_gloves`.

**Expected:** `gloves` epistemic status -> `UNKNOWN` -> pessimistic closure -> Tier 0 at
next restricted bind: *"Hands left the station. New gloves before starting."*
**Proves:** occlusion is an *input* to the design, not a failure of it — it degrades into
an 8-second action.

---

## Derived scenarios (also fixtures, lower priority)

| Id | Description | Proves |
|---|---|---|
| **I** | Back-contamination: `pesto -> gloves -> mayo tub`; later ticket uses mayo | The signature capability. **Required for demo.** |
| **J** | Wipe is not a reset: `pesto -> board`, `SURFACE_WIPE`, restricted item on board | `WIPE` does not clear taint |
| **K** | Tracker identity switch between two tools | Taint sets merge pessimistically |
| **L** | Camera fault mid-ticket | Clean transition to `PROTOCOL_ONLY`; existing holds persist |
| **M** | Alert storm suppression: 10s of continuous contact with one tainted tool | Exactly one alert, not forty |
