"""
A minimal Celery exporter that tracks celery_task_succeeded_total metric using Redis.
"""
import sys
import threading

from celery import Celery
from prometheus_client import Counter, CollectorRegistry, generate_latest
import redis

class CelerySuccessExporter:
    """
    A minimal Celery exporter that only tracks successful tasks using Redis.
    """
    def __init__(self, broker_url: str, redis_url: str = 'redis://localhost:6379/0'):
        print(f"Initializing exporter with broker={broker_url}, redis={redis_url}", file=sys.stderr)
        self.broker_url = broker_url
        self.redis_client = redis.Redis.from_url(redis_url)
        self.metrics_key = 'celery_metrics'
        
        self.app = Celery(broker=broker_url)
        self.state = self.app.events.State()
        
        # Initialize registry and metrics
        self.registry = CollectorRegistry()
        self.tasks_succeeded = Counter(
            'celery_task_succeeded_total',
            'Number of succeeded Celery tasks',
            registry=self.registry
        )
        
        # Set initial value if metrics exist in Redis
        stored_metrics = self.redis_client.get(self.metrics_key)
        if stored_metrics:
            print("Found existing metrics in Redis", file=sys.stderr)
            print(f"Metrics content:\n{stored_metrics.decode()}", file=sys.stderr)
            # Note: We don't need to parse and set the value since Counter starts at 0
            # and will be incremented by events
        else:
            # Store initial metrics
            self._store_metrics()
        
        # Event handlers mapping
        self.handlers = {
            'task-succeeded': self._handle_task_succeeded
        }
        
        self._stop_event = threading.Event()
        self._thread = None

    def _handle_task_succeeded(self, event):
        """Handle task-succeeded events by incrementing the counter."""
        print(f"Received task-succeeded event: {event.get('uuid')}", file=sys.stderr)
        self.tasks_succeeded.inc()
        self._store_metrics()

    def _store_metrics(self):
        """Store current metrics in Redis."""
        try:
            metrics = generate_latest(self.registry)
            self.redis_client.set(self.metrics_key, metrics)
            print(f"Updated metrics stored in Redis", file=sys.stderr)
            print(f"Metrics content:\n{metrics.decode()}", file=sys.stderr)
        except Exception as e:
            print(f"Error storing metrics: {e}", file=sys.stderr)

    def start(self):
        """Start monitoring Celery events."""
        print("Starting Celery event monitoring...", file=sys.stderr)
        def _monitor():
            with self.app.connection() as connection:
                print("Connected to broker, starting event capture...", file=sys.stderr)
                recv = self.app.events.Receiver(
                    connection, 
                    handlers=self.handlers
                )
                recv.capture(limit=None, timeout=None, wakeup=True)

        self._thread = threading.Thread(target=_monitor, daemon=True)
        self._thread.start()
        print("Monitor thread started", file=sys.stderr)

    def stop(self):
        """Stop monitoring Celery events."""
        print("Stopping exporter...", file=sys.stderr)
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        print("Exporter stopped", file=sys.stderr) 