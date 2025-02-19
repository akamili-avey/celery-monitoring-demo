from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def add(self, x, y):
    """Sample task that adds two numbers."""
    try:
        return x + y
    except Exception as exc:
        logger.error(f"Error in add task: {exc}")
        self.retry(exc=exc, countdown=5)

@shared_task(bind=True, max_retries=3)
def multiply(self, x, y):
    """Sample task that multiplies two numbers."""
    try:
        return x * y
    except Exception as exc:
        logger.error(f"Error in multiply task: {exc}")
        self.retry(exc=exc, countdown=5) 