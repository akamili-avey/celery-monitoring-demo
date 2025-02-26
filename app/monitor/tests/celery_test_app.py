"""
Test Celery application.
"""
import os
import time
from celery import Celery

os.environ['DJANGO_SETTINGS_MODULE'] = '' # prevent auto import of django settings

# Create the test app
app = Celery('test_app', broker='amqp://guest:guest@localhost:5674//')

# Enable events
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

@app.task
def test_task():
    """A test task that always succeeds."""
    # Just succeed without returning a value
    pass

@app.task
def failing_task():
    """A test task that always fails."""
    # Raise an exception to simulate a failing task
    raise ValueError("This task is designed to fail for testing purposes")

@app.task
def delayed_task(delay_seconds=0.5):
    """A test task that sleeps for a specified amount of time before succeeding."""
    print(f"Delayed task sleeping for {delay_seconds} seconds")
    time.sleep(delay_seconds)
    return f"Slept for {delay_seconds} seconds" 