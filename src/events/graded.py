from .catalog import Event, GradedEvent as GradedEvent, GRADEDEVENT_ADAPTER


def project(event: Event) -> GradedEvent:
    """ADR-0004: omit confidence structurally, not just by convention."""
    return GRADEDEVENT_ADAPTER.validate_python(event.model_dump(exclude={"confidence"}))
