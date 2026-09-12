"""Perception (layers 1-4 of `10`): frames -> detections -> tracks -> events, per `21`.

Deterministic techniques only (39 §3): ArUco corners for the station frame, HSV colour for
gloves, ArUco tags for tool identity, point-in-polygon + dwell + hysteresis for episodes.
Imports only `src.domain` and `src.events`; writes only to `EventSink`; persists no frame.
Requires the `perception` extra (opencv, numpy); nothing in the core imports this package.
"""

from .config import PerceptionConfig as PerceptionConfig
from .pipeline import Handle as Handle
from .pipeline import PerceptionPipeline as PerceptionPipeline
