"""Re-export from canonical Phase 4 package."""
from phase4.observability.logger import (  # noqa: F401
    REQUIRED_FIELDS,
    LoggedEvent,
    clear_logged_events,
    get_logged_events,
    log_event,
)

__all__ = [
    "REQUIRED_FIELDS",
    "LoggedEvent",
    "clear_logged_events",
    "get_logged_events",
    "log_event",
]
