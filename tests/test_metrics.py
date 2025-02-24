"""
Integration tests for the Celery metrics exporter.
"""
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import TestCase
import multiprocessing
import re

from app.metrics.exporter import CelerySuccessExporter
from tests.celery_app import test_task, app

def run_worker(app):
    """Function to run in a separate process as the Celery worker."""
    # Enable events
    app.conf.worker_send_task_events = True
    app.conf.task_send_sent_event = True
    
    worker = app.Worker(
        loglevel='INFO',
        concurrency=1,
        events=True,  # Enable events explicitly
    )
    worker.start()

class TestCelerySuccessExporter(TestCase):
    """Integration tests for CelerySuccessExporter."""
    
    def setUp(self):
        """Set up test environment."""
        self.broker_url = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5674//')
        
        # Create a temporary file for metrics
        self.metrics_file = tempfile.mktemp()
        print(f"Created metrics file at {self.metrics_file}", file=sys.stderr)
        
        # Create and start the exporter
        self.exporter = CelerySuccessExporter(self.broker_url, self.metrics_file)
        self.exporter.start()

        # Start Celery worker in a separate process
        self.worker_process = multiprocessing.Process(
            target=run_worker,
            args=(app,)
        )
        self.worker_process.start()
        print("Started Celery worker process", file=sys.stderr)
        
        # Give the worker time to initialize
        time.sleep(2)
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop the exporter
        self.exporter.stop()
        
        # Terminate the worker process
        if self.worker_process.is_alive():
            self.worker_process.terminate()
            self.worker_process.join(timeout=1)
            print("Stopped Celery worker process", file=sys.stderr)
        
        # Clean up metrics file
        try:
            Path(self.metrics_file).unlink()
        except FileNotFoundError:
            pass
    
    def read_metric_value(self) -> float:
        """Read the current value of celery_task_succeeded_total from the metrics file."""
        try:
            metrics_content = Path(self.metrics_file).read_bytes().decode()
            print(f"Raw metrics content:\n{metrics_content}", file=sys.stderr)
            
            # Look for the metric line and extract its value
            for line in metrics_content.splitlines():
                if line.startswith('celery_task_succeeded_total '):
                    value = float(line.split()[1])
                    print(f"Found metric value: {value}", file=sys.stderr)
                    return value
                    
            print("No celery_task_succeeded_total metric found", file=sys.stderr)
            return 0.0
        except FileNotFoundError:
            print(f"Metrics file not found: {self.metrics_file}", file=sys.stderr)
            return 0.0
    
    def wait_for_metric_value(self, expected_value: float, timeout: int = 5) -> float:
        """Wait for the metric to reach the expected value or timeout."""
        start_time = time.time()
        current_value = self.read_metric_value()
        
        while time.time() - start_time < timeout:
            current_value = self.read_metric_value()
            print(f"Current metric value: {current_value}", file=sys.stderr)
            if current_value >= expected_value:
                break
            time.sleep(0.1)
            
        return current_value
    
    def test_task_success_metrics(self):
        """Test that the success metric correctly tracks task completions."""
        # Get initial metric value
        initial_value = self.read_metric_value()
        print(f"Initial metric value: {initial_value}", file=sys.stderr)
        
        # Test single task
        test_task.delay()
        print("First task submitted", file=sys.stderr)
        
        # Wait for first task completion and verify
        first_value = self.wait_for_metric_value(initial_value + 1)
        self.assertEqual(first_value, initial_value + 1, 
                        "Metric value did not increase after first task")
        
        # Test batch of tasks
        batch_size = 3
        for i in range(batch_size):
            test_task.delay()
        print(f"Batch of {batch_size} tasks submitted", file=sys.stderr)
        
        # Wait for batch completion and verify
        final_value = self.wait_for_metric_value(first_value + batch_size)
        self.assertEqual(final_value, first_value + batch_size, 
                        f"Metric value did not increase by {batch_size} after submitting batch of tasks")
        
        # Verify total number of tasks
        total_tasks = batch_size + 1  # batch + first task
        self.assertEqual(final_value, initial_value + total_tasks,
                        f"Final metric value {final_value} does not match expected {initial_value + total_tasks}") 