"""apps/core/middleware.py — custom middleware for observability and security."""

import uuid
from typing import Callable

import structlog
from django.http import HttpRequest, HttpResponse


class RequestIDMiddleware:
    """
    Assigns a unique request ID to each incoming request.
    Useful for distributed tracing and log correlation.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.id = request_id  # type: ignore

        # Bind request_id to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        # Clear context after request
        structlog.contextvars.clear_contextvars()
        return response


class SecurityHeadersMiddleware:
    """Attach baseline hardening headers not covered by Django defaults."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "same-origin")
        return response


def pii_masking_processor(logger, log_method, event_dict):
    """
    Structlog processor to mask PII (email, phone) in logs.
    """
    if "email" in event_dict:
        email = event_dict["email"]
        if isinstance(email, str) and "@" in email:
            try:
                name, domain = email.split("@", 1)
                event_dict["email"] = f"{name[:2]}***@{domain}"
            except Exception:
                event_dict["email"] = "***MASKED***"

    if "phone" in event_dict:
        phone = event_dict["phone"]
        if isinstance(phone, str) and len(phone) > 4:
            event_dict["phone"] = f"***-***-{phone[-4:]}"

    return event_dict
