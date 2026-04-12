from __future__ import annotations

from dataclasses import dataclass

from src.integrations.google_mcp.booking_mcp_executor import BookingMcpExecutionError


class ParseLayerError(RuntimeError):
    pass


class DomainLayerError(RuntimeError):
    pass


class IntegrationLayerError(RuntimeError):
    pass


class SystemLayerError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecoveryPlan:
    error_type: str
    fallback_message: str
    next_state: str = "error_recover"


def classify_error(exc: Exception) -> str:
    if isinstance(exc, ParseLayerError):
        return "parse"
    if isinstance(exc, DomainLayerError):
        return "domain"
    if isinstance(exc, (IntegrationLayerError, BookingMcpExecutionError)):
        return "integration"
    return "system"


def build_recovery_plan(exc: Exception) -> RecoveryPlan:
    error_type = classify_error(exc)
    if error_type == "parse":
        return RecoveryPlan(
            error_type=error_type,
            fallback_message="I could not understand that request. Please rephrase and try again.",
        )
    if error_type == "domain":
        return RecoveryPlan(
            error_type=error_type,
            fallback_message="I could not complete that request with the provided details. Please try again.",
        )
    if error_type == "integration":
        return RecoveryPlan(
            error_type=error_type,
            fallback_message=(
                "We could not complete one or more booking artifacts right now. "
                "Please try again shortly."
            ),
        )
    return RecoveryPlan(
        error_type=error_type,
        fallback_message="Something unexpected happened. Please try again shortly.",
    )
