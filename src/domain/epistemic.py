"""13 §Epistemic status, evaluated at query time. The reducer never runs a timer; staleness is
a function of (carrier, now, config) where `now` is always an event's t_occurred."""

from __future__ import annotations

from .models import Carrier, Config, EpistemicStatus


def effective_epistemic(carrier: Carrier, t_now: int, cfg: Config) -> EpistemicStatus:
    if carrier.epistemic != EpistemicStatus.TRACKED:
        return carrier.epistemic
    if carrier.last_observed_at is None:
        return EpistemicStatus.UNKNOWN
    if t_now - carrier.last_observed_at > cfg.t_stale[carrier.kind]:
        return EpistemicStatus.STALE
    return EpistemicStatus.TRACKED
