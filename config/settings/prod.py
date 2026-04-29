"""config/settings/prod.py — production hardening."""
from .base import *  # noqa: F401, F403
import sentry_sdk
from decouple import config

DEBUG = False

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# ── Security ─────────────────────────────────────────────────────
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Sentry ────────────────────────────────────────────────────────
_sentry_dsn: str = config("SENTRY_DSN", default="")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
    )

# ── Logging (structlog-ready) ─────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processors": [
                "structlog.contextvars.merge_contextvars",
                "structlog.processors.add_log_level",
                "structlog.processors.TimeStamper",
                "structlog.stdlib.ProcessorFormatter.wrap_for_formatter",
            ],
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
