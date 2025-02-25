"""
A minimal Celery exporter that tracks celery_task_succeeded_total metric using Redis.
"""
import sys
import threading
import time

from celery import Celery
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest
import redis

class CelerySuccessExporter:
    """
    A minimal Celery exporter that tracks Celery task metrics using Redis.
    Metrics are periodically written to Redis rather than on every event.
    """
    def __init__(self, broker_url: str, redis_url: str = 'redis://localhost:6379/0', update_interval: float = 0.5):
        print(f"Initializing exporter with broker={broker_url}, redis={redis_url}", file=sys.stderr)
        self.broker_url = broker_url
        self.redis_client = redis.Redis.from_url(redis_url)
        self.metrics_key = 'celery_metrics'
        self.update_interval = update_interval  # Update interval in seconds
        
        self.app = Celery(broker=broker_url)
        self.state = self.app.events.State()
        
        # Initialize registry and metrics
        self.registry = CollectorRegistry()
        
        # Task success counter
        self.tasks_succeeded = Counter(
            'celery_task_succeeded_total',
            'Number of succeeded Celery tasks',
            registry=self.registry
        )
        
        # Task received counter
        self.tasks_received = Counter(
            'celery_task_received_total',
            'Number of received Celery tasks',
            registry=self.registry
        )
        
        # Task failed counter
        self.tasks_failed = Counter(
            'celery_task_failed_total',
            'Number of failed Celery tasks',
            registry=self.registry
        )
        
        # Task runtime histogram
        self.task_runtime = Histogram(
            'celery_task_runtime_seconds',
            'Histogram of Celery task runtime in seconds',
            ['task_name', 'state'],  # Labels for task name and state (success/failure)
            registry=self.registry,
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
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
            'task-succeeded': self._handle_task_succeeded,
            'task-received': self._handle_task_received,
            'task-failed': self._handle_task_failed
        }
        
        # Flags for thread control
        self._stop_event = threading.Event()
        self._metrics_updated = threading.Event()
        
        # Threads
        self._monitor_thread = None
        self._redis_thread = None
        
        # Metrics update tracking
        self._metrics_dirty = False
        self._last_update_time = time.time()

    def _handle_task_succeeded(self, event):
        """Handle task-succeeded events by incrementing the counter and recording runtime."""
        task_uuid = event.get('uuid')
        print(f"Received task-succeeded event: {task_uuid}", file=sys.stderr)
        self.tasks_succeeded.inc()
        
        # Update the state with this event
        self.state.event(event)
        
        # Get the task from the state
        task = self.state.tasks.get(task_uuid)
        
        if task:
            print(f"Task found in state: {task}", file=sys.stderr)
            task_name = task.name or 'unknown'
            
            # Get the runtime from the event directly
            runtime = event.get('runtime')
            if runtime is not None:
                print(f"Task {task_uuid} ({task_name}) succeeded in {runtime:.3f}s", file=sys.stderr)
                
                # Record runtime in histogram
                print(f"Recording runtime {runtime}s for task {task_name} (success) in histogram", file=sys.stderr)
                self.task_runtime.labels(task_name=task_name, state='success').observe(runtime)
                
                # Debug: Print current histogram metrics
                metrics = generate_latest(self.registry).decode()
                histogram_lines = [line for line in metrics.splitlines() if 'celery_task_runtime_seconds' in line]
                print(f"Current histogram metrics:\n" + "\n".join(histogram_lines), file=sys.stderr)
            else:
                print(f"Task {task_uuid} has no runtime in event", file=sys.stderr)
        else:
            print(f"No task found in state for task {task_uuid}", file=sys.stderr)
        
        # Mark metrics as needing update but don't write to Redis immediately
        self._metrics_dirty = True
        self._metrics_updated.set()  # Signal that metrics have been updated

    def _handle_task_received(self, event):
        """Handle task-received events by incrementing the counter."""
        task_uuid = event.get('uuid')
        print(f"Received task-received event: {task_uuid}", file=sys.stderr)
        self.tasks_received.inc()
        
        # Update the state with this event
        self.state.event(event)
        
        # Mark metrics as needing update but don't write to Redis immediately
        self._metrics_dirty = True
        self._metrics_updated.set()  # Signal that metrics have been updated

    def _handle_task_failed(self, event):
        """Handle task-failed events by incrementing the counter."""
        task_uuid = event.get('uuid')
        print(f"Received task-failed event: {task_uuid}", file=sys.stderr)
        self.tasks_failed.inc()
        
        # Update the state with this event
        self.state.event(event)
        
        # Get the task from the state
        task = self.state.tasks.get(task_uuid)
        
        if task:
            task_name = task.name or 'unknown'
            print(f"Task {task_uuid} ({task_name}) failed", file=sys.stderr)
        else:
            print(f"No task found in state for task {task_uuid}", file=sys.stderr)
        
        # Mark metrics as needing update but don't write to Redis immediately
        self._metrics_dirty = True
        self._metrics_updated.set()  # Signal that metrics have been updated

    def _store_metrics(self):
        """Store current metrics in Redis."""
        try:
            metrics = generate_latest(self.registry)
            self.redis_client.set(self.metrics_key, metrics)
            print(f"Updated metrics stored in Redis", file=sys.stderr)
            print(f"Metrics content:\n{metrics.decode()}", file=sys.stderr)
            
            # Reset the dirty flag and update time
            self._metrics_dirty = False
            self._last_update_time = time.time()
        except Exception as e:
            print(f"Error storing metrics: {e}", file=sys.stderr)

    def _redis_updater(self):
        """Thread function that periodically updates Redis with the latest metrics."""
        print(f"Starting Redis updater thread (interval: {self.update_interval}s)", file=sys.stderr)
        
        while not self._stop_event.is_set():
            # Wait for either a metrics update or the update interval
            # This allows us to update immediately if there's a burst of events
            # but also ensures we don't wait longer than update_interval
            timeout_reached = not self._metrics_updated.wait(timeout=self.update_interval)
            
            # If we were woken up by a metrics update or if the timeout was reached
            current_time = time.time()
            time_since_last_update = current_time - self._last_update_time
            
            if self._metrics_dirty or (timeout_reached and time_since_last_update >= self.update_interval):
                print(f"Updating Redis (dirty: {self._metrics_dirty}, time since last update: {time_since_last_update:.2f}s)", file=sys.stderr)
                self._store_metrics()
            
            # Reset the event for the next wait
            self._metrics_updated.clear()
    
    def _monitor_events(self):
        """Thread function that monitors Celery events."""
        with self.app.connection() as connection:
            print("Connected to broker, starting event capture...", file=sys.stderr)
            recv = self.app.events.Receiver(
                connection, 
                handlers=self.handlers
            )
            recv.capture(limit=None, timeout=None, wakeup=True)

    def start(self):
        """Start monitoring Celery events and the Redis updater thread."""
        print("Starting Celery event monitoring and Redis updater...", file=sys.stderr)
        
        # Start the Redis updater thread
        self._redis_thread = threading.Thread(target=self._redis_updater, daemon=True)
        self._redis_thread.start()
        
        # Start the event monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_events, daemon=True)
        self._monitor_thread.start()
        
        print("All threads started", file=sys.stderr)

    def stop(self):
        """Stop monitoring Celery events and the Redis updater."""
        print("Stopping exporter...", file=sys.stderr)
        
        # Signal threads to stop
        self._stop_event.set()
        self._metrics_updated.set()  # Wake up the Redis updater thread
        
        # Wait for threads to finish
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        if self._redis_thread:
            self._redis_thread.join(timeout=1.0)
        
        # Do a final update to Redis
        if self._metrics_dirty:
            print("Performing final Redis update before shutdown", file=sys.stderr)
            self._store_metrics()
        
        print("Exporter stopped", file=sys.stderr) 