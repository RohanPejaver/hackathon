# Human Interaction Model

The user is a line cook with both hands occupied, under time pressure, who did not ask for
this system. Every design choice follows from that.

## Design constraints

1. **No dashboard.** There is no moment during service to inspect one.
2. **Glanceable in < 1 second.** Headline <= 6 words; required actions as icons + nouns.
3. **<= 2 taps to resolve anything.** Measured, not assumed (`34`).
4. **Silence is the default state** and is the feature that makes the rest tolerable.
5. **Never accusatory.** The system reports what it observed and did not observe; it never
   tells a person they contaminated something (`02`).
6. **No per-person feedback, ever.** No scores, no streaks, no "you forgot again." The
   moment the display becomes a performance instrument, cooperation ends (`24`).

## The three surfaces

### Tier 0 — Reset Prompt (the primary surface)

Appears at `TICKET_BOUND`, before any motion. A checklist:

```
  PINE NUT — station not clean
  [ ] New gloves
  [ ] Clean spreader
  ! Mayo container flagged — use sealed backup
```

Items **tick themselves off** as resets are observed. Compliance reads as progress, not
paperwork. This is the surface that carries most of the system's value and it must feel like
help, not interrogation.

### Tier 1 — Interrupt

A single line, dismissible, during prep. Fires only on `OBSERVED` pathways. Shows the
specific carrier and the specific action:

```
  STOP — spreader touched pesto.  [Swap tool]  [Already swapped]
```

### Tier 2 — Hold at the pass

The only blocking surface. Does not auto-clear. Shows the evidence trace (`25`) and the
epistemic disclaimer:

```
  HOLD — TICKET 48 — DO NOT SEND
  PINE_NUT. Spreader contacted pesto 14:31:52. Replacement not observed.
  This is an observation, not a determination. Confirm with the cook.
  [Cook confirms tool was clean]     [Remake]
```

## Worker actions

| Action | Effect | Grade |
|---|---|---|
| **Acknowledge** | Alert -> `ACKNOWLEDGED`. Does **not** clear taint. | — |
| **"Already swapped" / "Already clean"** | `OPERATOR_ASSERTION` -> taint cleared | `ASSERTED` |
| **Dismiss** (Tier 0/1 only) | Alert hidden for `t_cooldown`; state unchanged; logged | — |
| **Remake** | Ticket -> `VOIDED`, rework opened | — |
| **Resolve hold** (Tier 2) | Explicit human release. The only path out of `HELD`. | — |

Every action enters as an **event in the same log** (`10`) — replayable, auditable, and
part of the scenario suite. Corrections are not a side channel.

## What dismissal does and does not mean

Dismissal suppresses the *display*; it never clears *state*. A dismissed Tier 1 whose
pathway is still open will re-raise after cooldown, and will still escalate to Tier 2 at
completion. This is the one place the system deliberately does not defer to the human,
because the alternative is an instrument that can be silenced into uselessness — and Tier 2
is precisely the moment where a second opinion is cheapest relative to its cost.

Dismissal rate per carrier is tracked as a **system** health metric (is this zone badly
authored?), never as a **person** metric.

## Handling false alerts

The epistemic framing is what makes false alerts survivable. *"Replacement not observed"*
invites "I did swap it" -> one tap -> resolved. *"You contaminated this"* invites an
argument the system cannot win and a worker who stops trusting it.

Every assertion is logged with its grade, so a high assertion rate on one carrier surfaces a
perception defect rather than blaming an operator.

## Escalation to a second human

Tier 2 unresolved past `t_manager` surfaces to a manager. **Deferred post-MVP** — recorded
because the alert model (`16`) already reserves the transition.
