"""
A minimal Celery exporter that tracks celery_task_succeeded_total metric.
"""
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from celery import Celery
from celery.events.state import State
from prometheus_client import Counter, CollectorRegistry, generate_latest

class CelerySuccessExporter:
    """
    A minimal Celery exporter that only tracks successful tasks.
    """
    def __init__(self, broker_url: str, output_file: str):
        print(f"Initializing exporter with broker={broker_url}", file=sys.stderr)
        self.broker_url = broker_url
        self.output_file = Path(output_file)
        
        # Create the file if it doesn't exist
        self.output_file.touch()
        print(f"Created/touched metrics file at {self.output_file}", file=sys.stderr)
        
        self.app = Celery(broker=broker_url)
        self.state = self.app.events.State()
        
        # Initialize registry and metrics
        self.registry = CollectorRegistry()
        self.tasks_succeeded = Counter(
            'celery_task_succeeded_total',
            'Number of succeeded Celery tasks',
            registry=self.registry
        )
        
        # Write initial metrics
        self._write_metrics()
        
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
        self._write_metrics()

    def _write_metrics(self):
        """Write current metrics to the output file."""
        try:
            metrics = generate_latest(self.registry)
            self.output_file.write_bytes(metrics)
            print(f"Updated metrics written to {self.output_file}", file=sys.stderr)
            print(f"Metrics content:\n{metrics.decode()}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing metrics: {e}", file=sys.stderr)

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

    def get_metrics(self) -> bytes:
        """Get the current metrics in Prometheus format."""
        return generate_latest(self.registry) 