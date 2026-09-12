"""Assertion vocabulary (36 §Assertion vocabulary) evaluated against a `ReplayResult`.

Each `expect` entry is `{ <assertion>: <body> }`, optionally with a sibling `at` (the 36
example writes `{ at: 1000, alert: {...} }`); a body may also carry its own `at`. An unknown
or malformed assertion FAILS rather than being skipped, so a typo cannot pass silently.

Vocabulary beyond 36 (each addition is named in the final report): `silence`, `held`,
`alert_open`, `raise_count`, `no_alerts_of_tier.before`, `alert.blocking_carriers_include`,
`pathway.includes` / `pathway.target`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from pydantic import JsonValue

from src.domain import AlertCommand, TicketLifecycle, WorldState

from .schema import AssertionResult, ReplayResult, StateSnapshot

_RAISING = ("RAISE", "ESCALATE")
_Body = Mapping[str, JsonValue]
_Check = Callable[[JsonValue, int | None, ReplayResult], tuple[bool, str]]


def evaluate_assertions(
    expect: list[dict[str, JsonValue]], run: ReplayResult
) -> list[AssertionResult]:
    return [_evaluate_one(entry, run) for entry in expect]


def _evaluate_one(entry: Mapping[str, JsonValue], run: ReplayResult) -> AssertionResult:
    keys = sorted(set(entry) - {"at"})
    record = dict(entry)
    if len(keys) != 1 or keys[0] not in _CHECKS:
        return AssertionResult(assertion=record, passed=False, detail=f"unknown assertion {keys!r}")
    name = keys[0]
    body = entry[name]
    at = _at_of(entry, body)
    try:
        passed, detail = _CHECKS[name](body, at, run)
    except (KeyError, TypeError, ValueError) as exc:
        passed, detail = False, f"malformed `{name}` assertion: {exc}"
    return AssertionResult(assertion=record, passed=passed, detail=detail)


def _at_of(entry: Mapping[str, JsonValue], body: JsonValue) -> int | None:
    inner = body.get("at") if isinstance(body, dict) else None
    value = inner if inner is not None else entry.get("at")
    return _int(value) if value is not None else None


# ---- alert commands ------------------------------------------------------------------------


def _raises(run: ReplayResult) -> list[tuple[int, AlertCommand]]:
    return [(tc.t, tc.command) for tc in run.commands if tc.command.kind in _RAISING]


def _describe(t: int, cmd: AlertCommand) -> str:
    a = cmd.alert
    return (
        f"t={t} {cmd.kind} tier={int(a.tier)} ticket={a.ticket_id} allergen={a.allergen_id} "
        f"blocking={a.blocking_carriers} state={a.state.value} headline={a.headline!r}"
    )


def _alert_matches(body: _Body, cmd: AlertCommand) -> bool:
    a = cmd.alert
    if "tier" in body and int(a.tier) != _int(body["tier"]):
        return False
    if "ticket" in body and a.ticket_id != body["ticket"]:
        return False
    if "allergen" in body and a.allergen_id != body["allergen"]:
        return False
    if "blocking_carriers" in body and sorted(a.blocking_carriers) != sorted(
        _strings(body["blocking_carriers"])
    ):
        return False
    if "blocking_carriers_include" in body and not set(
        _strings(body["blocking_carriers_include"])
    ) <= set(a.blocking_carriers):
        return False
    if "headline_contains" in body and (
        str(body["headline_contains"]).lower() not in a.headline.lower()
    ):
        return False
    return True


def _check_alert(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    since = at if at is not None else 0
    candidates = [(t, c) for t, c in _raises(run) if t >= since]
    if any(_alert_matches(spec, c) for _, c in candidates):
        return True, "matched"
    seen = "; ".join(_describe(t, c) for t, c in candidates) or "none"
    return False, f"no RAISE/ESCALATE at/after t={since} matched; seen: {seen}"


def _check_alert_resolved(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    since = at if at is not None else 0
    tier, reason = _int(spec["tier"]), str(spec["reason"])
    resolves = [
        (tc.t, tc.command) for tc in run.commands if tc.command.kind == "RESOLVE" and tc.t >= since
    ]
    for _, cmd in resolves:
        if int(cmd.alert.tier) == tier and cmd.alert.state.value == reason:
            return True, "matched"
    seen = "; ".join(_describe(t, c) for t, c in resolves) or "none"
    return False, f"no RESOLVE of tier {tier} with state {reason} at/after t={since}; seen: {seen}"


def _check_no_alerts_after(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    since = _int(body) if not isinstance(body, dict) else _int(body["at"])
    late = [(t, c) for t, c in _raises(run) if t > since]
    if not late:
        return True, f"no RAISE/ESCALATE after t={since}"
    return False, "; ".join(_describe(t, c) for t, c in late)


def _check_no_alerts_of_tier(
    body: JsonValue, at: int | None, run: ReplayResult
) -> tuple[bool, str]:
    spec = _body(body)
    tier = _int(spec["tier"])
    after = _int(spec["after"]) if "after" in spec else None
    before = _int(spec["before"]) if "before" in spec else None
    hits = [
        (t, c)
        for t, c in _raises(run)
        if int(c.alert.tier) == tier
        and (after is None or t > after)
        and (before is None or t < before)
    ]
    if not hits:
        return True, f"no tier-{tier} RAISE/ESCALATE in window"
    return False, "; ".join(_describe(t, c) for t, c in hits)


def _check_silence(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    if body is not True:
        raise ValueError("silence must be `true`")
    raised = _raises(run)
    if not raised:
        return True, "no RAISE/ESCALATE in the run"
    return False, "; ".join(_describe(t, c) for t, c in raised)


def _check_raise_count(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    tier, expected = _int(spec["tier"]), _int(spec["equals"])
    hits = [(t, c) for t, c in _raises(run) if int(c.alert.tier) == tier]
    if len(hits) == expected:
        return True, f"{expected} tier-{tier} RAISE/ESCALATE"
    seen = "; ".join(_describe(t, c) for t, c in hits) or "none"
    return False, f"expected {expected} tier-{tier} RAISE/ESCALATE, got {len(hits)}: {seen}"


def _check_alert_open(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    tier = _int(spec["tier"])
    if at is None:
        raise ValueError("alert_open requires `at`")
    last: dict[str, tuple[str, int]] = {}
    for tc in run.commands:
        if tc.t <= at:
            last[tc.command.alert.alert_id] = (tc.command.kind, int(tc.command.alert.tier))
    open_ids = sorted(
        alert_id
        for alert_id, (kind, alert_tier) in last.items()
        if kind in ("RAISE", "UPDATE", "ESCALATE") and alert_tier == tier
    )
    if open_ids:
        return True, f"open tier-{tier} alerts at t={at}: {open_ids}"
    return False, f"no open tier-{tier} alert at t={at}; last commands: {sorted(last.items())}"


# ---- state ----------------------------------------------------------------------------------


def _snapshot_at(run: ReplayResult, at: int) -> StateSnapshot | None:
    chosen: StateSnapshot | None = None
    for snap in run.states:
        if snap.t <= at:
            chosen = snap
    return chosen


def _match_state(spec: _Body, state: WorldState) -> list[str]:
    problems: list[str] = []
    unknown = sorted(set(spec) - {"carriers", "conditions", "tickets", "at"})
    if unknown:
        problems.append(f"unknown state keys {unknown}")
    for carrier_id, raw in sorted(_body(spec.get("carriers", {})).items()):
        carrier = state.station.carriers.get(carrier_id)
        if carrier is None:
            problems.append(f"{carrier_id}: not in state")
            continue
        cspec = _body(raw)
        if "taints" in cspec:
            tspec = _body(cspec["taints"])
            if not tspec and carrier.taints:
                problems.append(f"{carrier_id}: expected no taints, has {sorted(carrier.taints)}")
            for allergen, fields in sorted(tspec.items()):
                record = carrier.taints.get(allergen)
                if record is None:
                    problems.append(f"{carrier_id}: missing taint {allergen}")
                    continue
                for name, want in sorted(_body(fields).items()):
                    have = getattr(record, name)
                    have = have.value if hasattr(have, "value") else have
                    if have != want:
                        problems.append(
                            f"{carrier_id}.taints.{allergen}.{name}: {have!r} != {want!r}"
                        )
        if "epistemic" in cspec and carrier.epistemic.value != cspec["epistemic"]:
            problems.append(
                f"{carrier_id}.epistemic: {carrier.epistemic.value} != {cspec['epistemic']!r}"
            )
    for condition in _strings(spec.get("conditions", [])):
        if condition not in state.conditions:
            problems.append(f"condition {condition} absent; have {state.conditions}")
    for ticket_id, raw in sorted(_body(spec.get("tickets", {})).items()):
        ticket = state.tickets.get(ticket_id)
        if ticket is None:
            problems.append(f"ticket {ticket_id}: not in state")
            continue
        want = _body(raw).get("lifecycle")
        if want is not None and ticket.lifecycle.value != want:
            problems.append(f"ticket {ticket_id}.lifecycle: {ticket.lifecycle.value} != {want!r}")
    return problems


def _check_final_state(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    problems = _match_state(_body(body), run.final_state)
    return (not problems), ("; ".join(problems) or "matched")


def _check_state_at(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    if at is None:
        raise ValueError("state_at requires `at`")
    snap = _snapshot_at(run, at)
    if snap is None:
        return False, f"no state at or before t={at}"
    problems = _match_state(_body(body), snap.state)
    return (not problems), ("; ".join(problems) or f"matched state after {snap.event_id}")


def _check_mode(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    if at is None:
        raise ValueError("mode requires `at`")
    want = str(spec["mode"])
    mode = run.mode_timeline[0].mode if run.mode_timeline else None
    for change in run.mode_timeline:
        if change.t <= at:
            mode = change.mode
    have = mode.value if mode is not None else "<no mode recorded>"
    return have == want, f"mode at t={at} is {have}"


def _check_held(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    ticket_id = str(spec["ticket"])
    since = at if at is not None else 0
    for snap in run.states:
        ticket = snap.state.tickets.get(ticket_id)
        if snap.t >= since and ticket is not None and ticket.lifecycle == TicketLifecycle.HELD:
            return True, f"{ticket_id} HELD after {snap.event_id} (t={snap.t})"
    final = run.final_state.tickets.get(ticket_id)
    have = final.lifecycle.value if final is not None else "<absent>"
    return False, f"{ticket_id} never HELD at/after t={since}; final lifecycle {have}"


# ---- pathways, rejections ---------------------------------------------------------------------


def _check_pathway(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    since = at if at is not None else 0
    nodes = _strings(spec["nodes"]) if "nodes" in spec else None
    includes = _strings(spec["includes"]) if "includes" in spec else None
    target = str(spec["target"]) if "target" in spec else None
    seen: list[list[str]] = []
    for tp in run.pathways:
        if tp.t < since:
            continue
        found = tp.pathway.nodes
        if found not in seen:
            seen.append(found)
        if nodes is not None and found != nodes:
            continue
        if includes is not None and not _subsequence(includes, found):
            continue
        if target is not None and (not found or found[-1] != target):
            continue
        return True, f"matched {found} at t={tp.t}"
    return False, f"no pathway at/after t={since} matched; seen: {seen or 'none'}"


def _subsequence(needle: list[str], haystack: list[str]) -> bool:
    position = 0
    for node in haystack:
        if position < len(needle) and node == needle[position]:
            position += 1
    return position == len(needle)


def _check_event_rejected(body: JsonValue, at: int | None, run: ReplayResult) -> tuple[bool, str]:
    spec = _body(body)
    index = _int(spec["index"]) if "index" in spec else None
    suffix = str(spec["event_id_suffix"]) if "event_id_suffix" in spec else None
    if index is None and suffix is None:
        raise ValueError("event_rejected needs `index` or `event_id_suffix`")
    for rejection in run.rejected:
        if index is not None and rejection.index != index:
            continue
        if suffix is not None and not rejection.event_id.endswith(suffix):
            continue
        return True, f"rejected {rejection.event_id}: {rejection.reason}"
    return False, f"no matching rejection; recorded: {[r.event_id for r in run.rejected]}"


_CHECKS: dict[str, _Check] = {
    "alert": _check_alert,
    "alert_resolved": _check_alert_resolved,
    "no_alerts_after": _check_no_alerts_after,
    "no_alerts_of_tier": _check_no_alerts_of_tier,
    "silence": _check_silence,
    "raise_count": _check_raise_count,
    "alert_open": _check_alert_open,
    "final_state": _check_final_state,
    "state_at": _check_state_at,
    "mode": _check_mode,
    "held": _check_held,
    "pathway": _check_pathway,
    "event_rejected": _check_event_rejected,
}

VOCABULARY = frozenset(_CHECKS)


# ---- JsonValue helpers ------------------------------------------------------------------------


def _body(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"expected a mapping, got {value!r}")
    return value


def _int(value: JsonValue) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"expected an integer, got {value!r}")
    return value


def _strings(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"expected a list, got {value!r}")
    return [str(item) for item in value]
