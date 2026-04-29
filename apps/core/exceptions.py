"""apps/core/exceptions.py — project-wide exception definitions."""
from rest_framework.exceptions import APIException
from rest_framework import status


class ServiceError(Exception):
    """Base class for all service-layer exceptions."""


class InsufficientStockError(ServiceError):
    """Raised when stock is insufficient for an order line."""

    def __init__(self, product_id, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested={requested}, available={available}"
        )


class InvalidStatusTransitionError(ServiceError):
    """Raised when an FSM transition is not allowed."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition from {current!r} to {target!r}")


# ── DRF API exceptions ────────────────────────────────────────────

class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."
    default_code = "conflict"
