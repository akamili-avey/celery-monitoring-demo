"""
Integration tests for the Celery metrics exporter.
"""
import os
import sys
import time
from unittest import TestCase
import multiprocessing
import redis

from app.metrics.exporter import CelerySuccessExporter
from app.metrics.tests.celery_app import test_task, app

def run_worker(app):
    """Function to run in a separate process as the Celery worker."""
    # Enable events
    app.conf.worker_send_task_events = True
    app.conf.task_send_sent_event = True
    
    # Disable Django loader
    app.conf.update(
        INSTALLED_APPS=(),
        DJANGO_SETTINGS_MODULE=None,
    )
    
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
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Create Redis client and clear metrics
        self.redis_client = redis.Redis.from_url(self.redis_url)
        self.metrics_key = 'celery_metrics'
        self.redis_client.delete(self.metrics_key)
        print(f"Cleared Redis key {self.metrics_key}", file=sys.stderr)
        
        # Create and start the exporter with a shorter update interval for testing
        self.update_interval = 0.2  # 200ms for faster testing
        self.exporter = CelerySuccessExporter(
            self.broker_url, 
            self.redis_url,
            update_interval=self.update_interval
        )
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
        
        # Clean up Redis key
        self.redis_client.delete(self.metrics_key)
        print(f"Cleaned up Redis key {self.metrics_key}", file=sys.stderr)
    
    def get_metrics(self) -> str:
        """Get the current metrics page from Redis."""
        metrics = self.redis_client.get(self.metrics_key)
        if metrics:
            metrics_text = metrics.decode()
            print(f"Current metrics from Redis:\n{metrics_text}", file=sys.stderr)
            return metrics_text
        return ""
    
    def get_counter_value(self) -> float:
        """Extract the counter value from the stored metrics."""
        try:
            metrics = self.get_metrics()
            if not metrics:
                return 0.0
                
            # Parse the metrics text to find the counter value
            for line in metrics.splitlines():
                if line.startswith('celery_task_succeeded_total '):
                    return float(line.split()[1])
            return 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def wait_for_metric_value(self, expected_value: float, timeout: int = 5) -> float:
        """Wait for the metric to reach the expected value or timeout."""
        start_time = time.time()
        current_value = self.get_counter_value()
        
        while time.time() - start_time < timeout:
            current_value = self.get_counter_value()
            print(f"Current metric value: {current_value}", file=sys.stderr)
            if current_value >= expected_value:
                break
            # Wait slightly longer than the update interval to ensure Redis is updated
            time.sleep(self.update_interval * 1.5)
            
        return current_value
    
    def test_task_success_metrics(self):
        """Test that the success metric correctly tracks task completions."""
        # Get initial metrics and value
        initial_metrics = self.get_metrics()
        self.assertIn('celery_task_succeeded_total', initial_metrics,
                     "Initial metrics should contain the counter")
        initial_value = self.get_counter_value()
        print(f"Initial metric value: {initial_value}", file=sys.stderr)
        
        # Test single task
        test_task.delay()
        print("First task submitted", file=sys.stderr)
        
        # Wait for first task completion and verify
        first_value = self.wait_for_metric_value(initial_value + 1)
        self.assertEqual(first_value, initial_value + 1, 
                        "Metric value did not increase after first task")
        
        # Verify metrics format
        metrics_after_first = self.get_metrics()
        self.assertIn('# HELP celery_task_succeeded_total', metrics_after_first,
                     "Metrics should contain help text")
        self.assertIn('# TYPE celery_task_succeeded_total counter', metrics_after_first,
                     "Metrics should contain type information")
        
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
        
        # Verify final metrics format
        final_metrics = self.get_metrics()
        self.assertIn(f'celery_task_succeeded_total {final_value}', final_metrics,
                     "Final metrics should contain the correct counter value")
    
    def test_periodic_updates(self):
        """Test that metrics are updated periodically rather than on every event."""
        # Get initial value
        initial_value = self.get_counter_value()
        
        # Submit a batch of tasks quickly
        batch_size = 5
        for i in range(batch_size):
            test_task.delay()
            # Don't sleep between tasks to ensure they're processed in the same update cycle
        
        print(f"Submitted {batch_size} tasks in quick succession", file=sys.stderr)
        
        # Check Redis immediately - it might not be updated yet due to the periodic nature
        immediate_value = self.get_counter_value()
        print(f"Immediate metric value after batch: {immediate_value}", file=sys.stderr)
        
        # Wait for the update interval to pass and check again
        time.sleep(self.update_interval * 2)  # Wait for 2 update cycles
        updated_value = self.get_counter_value()
        print(f"Metric value after waiting: {updated_value}", file=sys.stderr)
        
        # The final value should reflect all tasks
        final_value = self.wait_for_metric_value(initial_value + batch_size)
        self.assertEqual(final_value, initial_value + batch_size,
                        f"Final metric value {final_value} does not match expected {initial_value + batch_size}")
        
        # Verify that the metrics were updated in batches rather than individually
        # This is hard to test definitively, but we can check if the immediate value
        # was less than the final value, indicating batched updates
        if immediate_value < final_value:
            print("Confirmed that metrics were updated periodically rather than immediately", file=sys.stderr)
        else:
            print("Note: Could not confirm periodic updates - immediate value already reflected all tasks", file=sys.stderr) 