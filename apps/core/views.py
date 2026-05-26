"""apps/core/views.py — local health-check view."""

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    GET /health/
    Returns JSON with DB, Redis, Celery, and overall local status.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth required for health probe

    @extend_schema(
        tags=["System"],
        responses=inline_serializer(
            name="HealthCheckResponse",
            fields={
                "status": serializers.CharField(),
                "services": serializers.DictField(child=serializers.BooleanField()),
            },
        ),
    )
    def get(self, request: Request) -> Response:
        status = {"db": False, "redis": False, "celery": False}

        # Check DB
        try:
            connection.ensure_connection()
            status["db"] = True
        except Exception:
            pass

        # Check Redis
        try:
            cache.set("_health_check", "ok", timeout=5)
            status["redis"] = cache.get("_health_check") == "ok"
        except Exception:
            pass

        # Check Celery workers through the configured broker.
        try:
            from config.celery import app

            ping = app.control.inspect(timeout=0.5).ping() or {}
            status["celery"] = bool(ping)
        except Exception:
            pass

        is_healthy = status["db"] and status["redis"]
        return Response(
            {"status": "ok" if is_healthy else "degraded", "services": status},
            status=200 if is_healthy else 503,
        )
