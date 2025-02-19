from celery import shared_task

@shared_task
def add(x, y):
    """Sample task that adds two numbers."""
    return x + y

@shared_task
def multiply(x, y):
    """Sample task that multiplies two numbers."""
    return x * y 