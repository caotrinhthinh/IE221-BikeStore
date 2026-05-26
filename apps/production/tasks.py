"""apps/production/tasks.py — Production background tasks."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def sync_inventory_report():
    """
    Generate and export inventory report (CSV).
    Kept as a simple optional local Celery demo task.
    """
    logger.info("Starting inventory sync report generation")
    # Export logic here
    return "Inventory report generated"
