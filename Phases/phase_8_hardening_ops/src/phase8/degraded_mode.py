"""Degraded mode messaging for MCP outage scenarios.

Provides user-safe messages when backend services (Calendar, Docs, Gmail)
are unreachable.  These messages MUST NOT claim artifact success and MUST
guide the user to retry or contact support.
"""

from __future__ import annotations

MCP_TIMEOUT_MESSAGE = (
    "We're experiencing a temporary delay connecting to our booking services. "
    "Your request has not been completed. Please try again in a few minutes."
)

MCP_PARTIAL_FAILURE_MESSAGE = (
    "We could not complete all booking steps right now. "
    "No booking has been finalized. Please try again shortly."
)

MCP_FULL_OUTAGE_MESSAGE = (
    "Our booking services are currently unavailable. "
    "Please try again later or contact support for assistance. "
    "No changes have been made to your appointments."
)

SERVICE_DEGRADED_MESSAGES: dict[str, str] = {
    "calendar": (
        "The calendar service is temporarily unavailable. "
        "No calendar hold was created. Please try again shortly."
    ),
    "docs": (
        "The document logging service is temporarily unavailable. "
        "Your calendar hold may have been created, but the booking is not finalized. "
        "Please try again or contact support."
    ),
    "gmail": (
        "The email drafting service is temporarily unavailable. "
        "Your calendar hold and document log may have been created, "
        "but the confirmation email was not drafted. "
        "Please try again or contact support."
    ),
}


def get_degraded_message(stage: str) -> str:
    """Return the appropriate degraded-mode message for a failure at *stage*."""
    return SERVICE_DEGRADED_MESSAGES.get(stage, MCP_FULL_OUTAGE_MESSAGE)


def is_timeout_error(exc: Exception) -> bool:
    """Heuristic check for timeout-class errors."""
    msg = str(exc).lower()
    return any(
        keyword in msg
        for keyword in ("timeout", "timed out", "deadline exceeded", "connect timeout")
    )
