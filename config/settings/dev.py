"""config/settings/dev.py — local development overrides."""

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts locally
ALLOWED_HOSTS = ["*"]

# Docker containers can resolve the Compose service hostname `db`, but commands
# run directly on the host cannot. Host development should use the published
# localhost ports while Docker services stay on the internal network.
RUNNING_IN_DOCKER = config("RUNNING_IN_DOCKER", default=False, cast=bool)

if not RUNNING_IN_DOCKER:
    local_db_host = config("DB_HOST", default="localhost")
    local_db_port = config("DB_PORT", default="5432")

    # If .env still points at the Docker-internal hostname, redirect to localhost
    # using the published host port so `python manage.py runserver` works on the host.
    if local_db_host in {"db", "postgres"}:
        local_db_host = "localhost"
        local_db_port = config("POSTGRES_HOST_PORT", default="5433")

    DATABASES["default"]["HOST"] = local_db_host  # noqa: F405
    DATABASES["default"]["PORT"] = local_db_port  # noqa: F405

    # Use in-memory cache so runserver works without a local Redis instance.
    CACHES = {  # noqa: F405
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"

# Relaxed email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Simplified logging for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
