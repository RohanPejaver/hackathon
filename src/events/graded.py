from .catalog import GRADEDEVENT_ADAPTER, Event
from .catalog import GradedEvent as GradedEvent


def project(event: Event) -> GradedEvent:
    """ADR-0004: omit confidence structurally, not just by convention."""
    return GRADEDEVENT_ADAPTER.validate_python(event.model_dump(exclude={"confidence"}))
