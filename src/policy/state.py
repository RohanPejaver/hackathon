"""AlertState — policy-owned, derived entirely from commands and the log (16, 22)."""

from __future__ import annotations

from src.domain import Alert, AlertCommand, AlertLifecycle, Config, Tier
from src.events.catalog import (
    GradedAlertAcknowledged,
    GradedAlertUpdated,
    GradedEvent,
    GradedTicketReleased,
    GradedTicketVoided,
)

OPEN_STATES = frozenset(
    {AlertLifecycle.RAISED, AlertLifecycle.ACKNOWLEDGED, AlertLifecycle.ESCALATED}
)
RESOLVED_STATES = frozenset(
    {
        AlertLifecycle.RESOLVED_BY_RESET,
        AlertLifecycle.RESOLVED_BY_ASSERTION,
        AlertLifecycle.RESOLVED_BY_REMAKE,
        AlertLifecycle.EXPIRED,
    }
)
_CONTENT_FIELDS = (
    "headline",
    "required_actions",
    "derivation",
    "body",
    "blocking_carriers",
)


class AlertState:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._alerts: dict[str, Alert] = {}
        self._seq: dict[str, int] = {}
        self._raises = 0
        self._cooldowns: dict[str, int] = {}
        self._suppressions: list[AlertCommand] = []

    # ---- queries -------------------------------------------------------------------------
    def open(self) -> list[Alert]:
        return sorted(
            (a for a in self._alerts.values() if a.state in OPEN_STATES),
            key=lambda a: (a.raised_at, self._seq[a.alert_id]),
        )

    def all(self) -> list[Alert]:
        return list(self._alerts.values())

    def by_key(self, alert_key: str) -> Alert | None:
        for a in self._alerts.values():
            if a.alert_key == alert_key and a.state in OPEN_STATES:
                return a
        return None

    def cooldowns(self) -> dict[str, int]:
        return dict(self._cooldowns)

    def suppressions(self) -> list[AlertCommand]:
        """Every SUPPRESS applied: "fired and was suppressed" is distinct from "did not
        fire" (16 §Cooldown)."""
        return list(self._suppressions)

    # ---- mutators ------------------------------------------------------------------------
    def _store(self, alert: Alert) -> Alert:
        if alert.alert_id not in self._seq:
            self._seq[alert.alert_id] = len(self._seq)
        self._alerts[alert.alert_id] = alert
        return alert

    def _target(self, cmd: AlertCommand) -> Alert | None:
        existing = self._alerts.get(cmd.alert.alert_id)
        if existing is not None and existing.state in OPEN_STATES:
            return existing
        return self.by_key(cmd.alert.alert_key)

    def _raise(self, cmd: AlertCommand) -> Alert:
        self._raises += 1
        return self._store(
            cmd.alert.model_copy(
                update={"alert_id": f"al-{self._raises}", "state": AlertLifecycle.RAISED}
            )
        )

    def _content(self, cmd: AlertCommand) -> dict[str, object]:
        update: dict[str, object] = {f: getattr(cmd.alert, f) for f in _CONTENT_FIELDS}
        update["updated_at"] = cmd.t_occurred
        return update

    def apply(self, cmd: AlertCommand) -> Alert:
        if cmd.kind == "SUPPRESS":
            self._suppressions.append(cmd)
            return cmd.alert
        existing = self._target(cmd)
        if cmd.kind == "RAISE" or existing is None:
            if cmd.kind == "RESOLVE":
                return cmd.alert
            if existing is None:
                return self._raise(cmd)
            return self._store(existing.model_copy(update=self._content(cmd)))
        if cmd.kind == "UPDATE":
            return self._store(existing.model_copy(update=self._content(cmd)))
        if cmd.kind == "ESCALATE":
            update = self._content(cmd)
            update["tier"] = Tier(max(int(existing.tier), int(cmd.alert.tier)))
            update["state"] = AlertLifecycle.ESCALATED
            return self._store(existing.model_copy(update=update))
        state = cmd.alert.state
        if state not in RESOLVED_STATES:
            state = AlertLifecycle.RESOLVED_BY_RESET
        if state == AlertLifecycle.RESOLVED_BY_ASSERTION:
            until = cmd.cooldown_until
            self._cooldowns[existing.alert_key] = (
                until if until is not None else cmd.t_occurred + self._cfg.t_cooldown
            )
        return self._store(
            existing.model_copy(update={"state": state, "updated_at": cmd.t_occurred})
        )

    def observe(self, e: GradedEvent) -> None:
        """Fold operator and ticket events from the log (26 §Worker actions). Idempotent."""
        if isinstance(e, GradedAlertAcknowledged):
            alert = self._alerts.get(e.alert_id)
            if alert is not None and alert.state in (
                AlertLifecycle.RAISED,
                AlertLifecycle.ESCALATED,
            ):
                self._store(
                    alert.model_copy(
                        update={
                            "state": AlertLifecycle.ACKNOWLEDGED,
                            "acknowledged_by_slot": e.worker_slot,
                            "updated_at": e.t_occurred,
                        }
                    )
                )
        elif isinstance(e, GradedAlertUpdated):
            if e.worker_slot is None or e.command is not None:
                return
            alert = self._alerts.get(e.alert_id)
            if alert is not None and alert.state in OPEN_STATES and alert.tier != Tier.HOLD:
                # Dismissal suppresses the display only; state is unchanged (26).
                self._store(
                    alert.model_copy(
                        update={"dismissed_until": e.t_occurred + self._cfg.t_cooldown}
                    )
                )
        elif isinstance(e, GradedTicketVoided):
            for alert in self.open():
                if alert.ticket_id != e.ticket:
                    continue
                state = (
                    AlertLifecycle.EXPIRED
                    if alert.tier == Tier.RESET
                    else AlertLifecycle.RESOLVED_BY_REMAKE
                )
                self._store(alert.model_copy(update={"state": state, "updated_at": e.t_occurred}))
        elif isinstance(e, GradedTicketReleased):
            for alert in self.open():
                if alert.ticket_id != e.ticket or alert.tier != Tier.HOLD:
                    continue
                self._cooldowns[alert.alert_key] = e.t_occurred + self._cfg.t_cooldown
                self._store(
                    alert.model_copy(
                        update={
                            "state": AlertLifecycle.RESOLVED_BY_ASSERTION,
                            "updated_at": e.t_occurred,
                        }
                    )
                )
