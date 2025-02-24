"""
Test Celery application.
"""
from celery import Celery

# Create the test app
app = Celery('test_app', broker='amqp://guest:guest@localhost:5674//')

# Enable events
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

@app.task
def test_task():
    """A test task that always succeeds."""
    return "success" 