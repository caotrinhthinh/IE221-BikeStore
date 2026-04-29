"""apps/core/views.py — health-check view for load-balancers."""
from django.db import connection
from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


class HealthCheckView(APIView):
    """
    GET /health/
    Returns JSON with DB, Redis, and overall status.
    Used by Docker health checks and load-balancer probes.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth required for health probe

    def get(self, request: Request) -> Response:
        status = {"db": False, "redis": False}

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

        is_healthy = all(status.values())
        return Response(
            {"status": "ok" if is_healthy else "degraded", "services": status},
            status=200 if is_healthy else 503,
        )
