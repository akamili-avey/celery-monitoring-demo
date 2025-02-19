from celery import shared_task
import logging
import time

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=0)
def add(self, x, y, delay=0, failure=False):
    """Sample task that adds two numbers with optional delay and failure."""
    try:
        if delay > 0:
            time.sleep(delay)
        if failure:
            raise Exception("Task failed as requested")
        return x + y
    except Exception as exc:
        logger.error(f"Error in add task: {exc}")
        self.retry(exc=exc, countdown=5)