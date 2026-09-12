"""Order-source adapters (17, 22): the only place a third-party schema may appear.

MVP: ``ManualEntrySource`` and ``FixtureSource``. No POS/delivery adapter exists yet — that
integration is explicitly deferred (17; engineering/38).
"""

from .fixture import FixtureSource as FixtureSource
from .manual import ManualEntrySource as ManualEntrySource
