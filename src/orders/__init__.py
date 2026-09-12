"""Orders: restriction normalization, ticket intake, lifecycle table, order sources (17, 22).

Public API (the integration contract shared with the reducer, replay runner and runtime)::

    normalize(raw_text, k, threshold=0.8) -> Restriction
    intake(ticket_id, restrictions_raw, k, *, t, station_id, event_id_prefix,
           threshold=0.8) -> list[DraftEvent]        # exactly one event
    can_transition(frm, to) -> bool                  # BLOCKED -> BOUND is False
    OrderSource (Protocol), ManualEntrySource, FixtureSource

Imports only ``src.domain`` and ``src.events`` (22 §Dependency direction).
"""

from .adapters import FixtureSource as FixtureSource
from .adapters import ManualEntrySource as ManualEntrySource
from .intake import intake as intake
from .lifecycle import TERMINAL_STATES as TERMINAL_STATES
from .lifecycle import TRANSITIONS as TRANSITIONS
from .lifecycle import can_transition as can_transition
from .lifecycle import reachable_from as reachable_from
from .normalizer import DEFAULT_THRESHOLD as DEFAULT_THRESHOLD
from .normalizer import normalize as normalize
from .source import OrderSource as OrderSource
