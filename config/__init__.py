"""config/__init__.py — set default Celery app."""
from .celery import app as celery_app

__all__ = ("celery_app",)
