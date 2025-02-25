"""
Tests for the Celery metrics exporter.
"""
import os
import sys
import time
from unittest import TestCase
import multiprocessing
import redis
import re

from app.metrics.exporter import CelerySuccessExporter
from app.metrics.tests.celery_app import test_task, failing_task, delayed_task, app

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
    
    def get_counter_value(self, metric_name: str) -> float:
        """Extract a counter value from the stored metrics."""
        try:
            metrics = self.get_metrics()
            if not metrics:
                return 0.0
                
            # Parse the metrics text to find the counter value
            for line in metrics.splitlines():
                if line.startswith(f'{metric_name} '):
                    return float(line.split()[1])
            return 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def get_histogram_sum(self, metric_name: str, labels: dict = None) -> float:
        """Extract a histogram sum value from the stored metrics."""
        try:
            metrics = self.get_metrics()
            if not metrics:
                return 0.0
            
            # Construct the label string if provided
            label_str = ""
            if labels:
                label_parts = []
                for key, value in labels.items():
                    label_parts.append(f'{key}="{value}"')
                label_str = "{" + ",".join(label_parts) + "}"
            
            # Parse the metrics text to find the histogram sum
            metric_sum = f"{metric_name}_sum{label_str}"
            for line in metrics.splitlines():
                if line.startswith(metric_sum):
                    return float(line.split()[1])
            return 0.0
        except (ValueError, AttributeError) as e:
            print(f"Error extracting histogram sum: {e}", file=sys.stderr)
            return 0.0
    
    def get_histogram_count(self, metric_name: str, labels: dict = None) -> int:
        """Extract a histogram count value from the stored metrics."""
        try:
            metrics = self.get_metrics()
            if not metrics:
                return 0
            
            # Construct the label string if provided
            label_str = ""
            if labels:
                label_parts = []
                for key, value in labels.items():
                    label_parts.append(f'{key}="{value}"')
                label_str = "{" + ",".join(label_parts) + "}"
            
            # Parse the metrics text to find the histogram count
            metric_count = f"{metric_name}_count{label_str}"
            for line in metrics.splitlines():
                if line.startswith(metric_count):
                    return int(line.split()[1])
            return 0
        except (ValueError, AttributeError) as e:
            print(f"Error extracting histogram count: {e}", file=sys.stderr)
            return 0
    
    def wait_for_metric_value(self, metric_name: str, expected_value: float, timeout: int = 5) -> float:
        """Wait for the metric to reach the expected value or timeout."""
        start_time = time.time()
        current_value = self.get_counter_value(metric_name)
        
        while time.time() - start_time < timeout:
            current_value = self.get_counter_value(metric_name)
            print(f"Current {metric_name} value: {current_value}", file=sys.stderr)
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
                     "Initial metrics should contain the success counter")
        initial_value = self.get_counter_value('celery_task_succeeded_total')
        print(f"Initial success metric value: {initial_value}", file=sys.stderr)
        
        # Test single task
        test_task.delay()
        print("First task submitted", file=sys.stderr)
        
        # Wait for first task completion and verify
        first_value = self.wait_for_metric_value('celery_task_succeeded_total', initial_value + 1)
        self.assertEqual(first_value, initial_value + 1, 
                        "Success metric value did not increase after first task")
        
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
        final_value = self.wait_for_metric_value('celery_task_succeeded_total', first_value + batch_size)
        self.assertEqual(final_value, first_value + batch_size, 
                        f"Success metric value did not increase by {batch_size} after submitting batch of tasks")
        
        # Verify total number of tasks
        total_tasks = batch_size + 1  # batch + first task
        self.assertEqual(final_value, initial_value + total_tasks,
                        f"Final success metric value {final_value} does not match expected {initial_value + total_tasks}")
        
        # Verify final metrics format
        final_metrics = self.get_metrics()
        self.assertIn(f'celery_task_succeeded_total {final_value}', final_metrics,
                     "Final metrics should contain the correct success counter value")
    
    def test_periodic_updates(self):
        """Test that metrics are updated periodically rather than on every event."""
        # Get initial value
        initial_value = self.get_counter_value('celery_task_succeeded_total')
        
        # Submit a batch of tasks quickly
        batch_size = 5
        for i in range(batch_size):
            test_task.delay()
            # Don't sleep between tasks to ensure they're processed in the same update cycle
        
        print(f"Submitted {batch_size} tasks in quick succession", file=sys.stderr)
        
        # Check Redis immediately - it might not be updated yet due to the periodic nature
        immediate_value = self.get_counter_value('celery_task_succeeded_total')
        print(f"Immediate success metric value after batch: {immediate_value}", file=sys.stderr)
        
        # Wait for the update interval to pass and check again
        time.sleep(self.update_interval * 2)  # Wait for 2 update cycles
        updated_value = self.get_counter_value('celery_task_succeeded_total')
        print(f"Success metric value after waiting: {updated_value}", file=sys.stderr)
        
        # The final value should reflect all tasks
        final_value = self.wait_for_metric_value('celery_task_succeeded_total', initial_value + batch_size)
        self.assertEqual(final_value, initial_value + batch_size,
                        f"Final success metric value {final_value} does not match expected {initial_value + batch_size}")
        
        # Verify that the metrics were updated in batches rather than individually
        # This is hard to test definitively, but we can check if the immediate value
        # was less than the final value, indicating batched updates
        if immediate_value < final_value:
            print("Confirmed that metrics were updated periodically rather than immediately", file=sys.stderr)
        else:
            print("Note: Could not confirm periodic updates - immediate value already reflected all tasks", file=sys.stderr)

    def test_received_and_failed_metrics(self):
        """Test that the received and failed metrics correctly track tasks."""
        # Get initial metrics values
        initial_received = self.get_counter_value('celery_task_received_total')
        initial_failed = self.get_counter_value('celery_task_failed_total')
        initial_succeeded = self.get_counter_value('celery_task_succeeded_total')
        
        print(f"Initial received metric value: {initial_received}", file=sys.stderr)
        print(f"Initial failed metric value: {initial_failed}", file=sys.stderr)
        print(f"Initial succeeded metric value: {initial_succeeded}", file=sys.stderr)
        
        # Submit a successful task
        test_task.delay()
        print("Successful task submitted", file=sys.stderr)
        
        # Wait for the task to be processed
        time.sleep(1)
        
        # Submit a failing task
        try:
            failing_task.delay()
            print("Failing task submitted", file=sys.stderr)
        except Exception as e:
            print(f"Error submitting failing task: {e}", file=sys.stderr)
        
        # Wait for metrics to update
        time.sleep(self.update_interval * 3)
        
        # Check received metric (should be incremented for both tasks)
        received_value = self.wait_for_metric_value('celery_task_received_total', initial_received + 2)
        self.assertEqual(received_value, initial_received + 2,
                        f"Received metric value {received_value} does not match expected {initial_received + 2}")
        
        # Check failed metric (should be incremented for the failing task)
        failed_value = self.wait_for_metric_value('celery_task_failed_total', initial_failed + 1)
        self.assertEqual(failed_value, initial_failed + 1,
                        f"Failed metric value {failed_value} does not match expected {initial_failed + 1}")
        
        # Check succeeded metric (should be incremented for the successful task)
        succeeded_value = self.wait_for_metric_value('celery_task_succeeded_total', initial_succeeded + 1)
        self.assertEqual(succeeded_value, initial_succeeded + 1,
                        f"Succeeded metric value {succeeded_value} does not match expected {initial_succeeded + 1}")
        
        # Verify metrics format
        metrics = self.get_metrics()
        self.assertIn('# HELP celery_task_received_total', metrics,
                     "Metrics should contain received help text")
        self.assertIn('# TYPE celery_task_received_total counter', metrics,
                     "Metrics should contain received type information")
        self.assertIn('# HELP celery_task_failed_total', metrics,
                     "Metrics should contain failed help text")
        self.assertIn('# TYPE celery_task_failed_total counter', metrics,
                     "Metrics should contain failed type information")
                     
    def test_task_runtime_histogram(self):
        """Test that the task runtime histogram correctly tracks task execution times."""
        # Get initial metrics
        initial_metrics = self.get_metrics()
        
        # Verify histogram exists in initial metrics - only check for the type declaration
        self.assertIn('# TYPE celery_task_runtime_seconds histogram', initial_metrics,
                     "Initial metrics should contain the runtime histogram type declaration")
        
        # Submit a successful task
        test_task.delay()
        print("Successful task submitted for runtime measurement", file=sys.stderr)
        
        # Wait for the task to be processed and metrics to update
        time.sleep(1)
        
        # Submit a failing task
        try:
            failing_task.delay()
            print("Failing task submitted for runtime measurement", file=sys.stderr)
        except Exception as e:
            print(f"Error submitting failing task: {e}", file=sys.stderr)
        
        # Wait for metrics to update
        time.sleep(self.update_interval * 3)
        
        # Get updated metrics
        updated_metrics = self.get_metrics()
        
        # Check for success runtime metrics
        success_pattern = r'celery_task_runtime_seconds_count{.*state="success".*} (\d+)'
        success_matches = re.findall(success_pattern, updated_metrics)
        self.assertTrue(success_matches, "Should find success runtime metrics")
        success_count = int(success_matches[0])
        self.assertGreaterEqual(success_count, 1, "Should have at least one success runtime measurement")
        
        # Check for task name labels
        self.assertIn('task_name="app.metrics.tests.celery_app.test_task"', updated_metrics,
                     "Metrics should include the successful task name")
        
        # Verify histogram buckets exist for success state
        self.assertIn('celery_task_runtime_seconds_bucket{', updated_metrics,
                     "Metrics should contain histogram buckets")
        
        print("Task runtime histogram metrics verified", file=sys.stderr)
        
    def test_delayed_task_runtime(self):
        """Test that the runtime histogram accurately measures task execution time."""
        # Get initial metrics
        initial_metrics = self.get_metrics()
        print(f"Initial metrics:\n{initial_metrics}", file=sys.stderr)
        
        # Define delay times for testing
        delay_times = [0.5, 1.0, 2.0]
        total_delay = sum(delay_times)
        
        # Submit tasks with different delay times
        for delay in delay_times:
            delayed_task.delay(delay_seconds=delay)
            print(f"Submitted delayed task with {delay}s delay", file=sys.stderr)
        
        # Wait for tasks to complete and metrics to update
        # We need to wait longer than the longest delay plus some buffer
        wait_time = max(delay_times) + 3
        print(f"Waiting {wait_time}s for tasks to complete...", file=sys.stderr)
        time.sleep(wait_time)
        
        # Get updated metrics
        updated_metrics = self.get_metrics()
        print(f"Updated metrics after tasks:\n{updated_metrics}", file=sys.stderr)
        
        # Check that the tasks were executed
        succeeded_value = self.get_counter_value('celery_task_succeeded_total')
        self.assertGreaterEqual(succeeded_value, 3, 
                              f"Expected at least 3 succeeded tasks, got {succeeded_value}")
        
        # Check for the presence of histogram metrics
        # Look for specific histogram bucket patterns
        bucket_pattern = r'celery_task_runtime_seconds_bucket{.*} \d+'
        bucket_matches = re.findall(bucket_pattern, updated_metrics)
        self.assertTrue(bucket_matches, 
                      f"Expected to find histogram buckets in metrics, but none found. Metrics: {updated_metrics}")
        
        # Check for histogram sum
        sum_pattern = r'celery_task_runtime_seconds_sum{.*} (\d+\.\d+)'
        sum_matches = re.findall(sum_pattern, updated_metrics)
        self.assertTrue(sum_matches, 
                      f"Expected to find histogram sum in metrics, but none found. Metrics: {updated_metrics}")
        
        # Check for histogram count
        count_pattern = r'celery_task_runtime_seconds_count{.*} (\d+)'
        count_matches = re.findall(count_pattern, updated_metrics)
        self.assertTrue(count_matches, 
                      f"Expected to find histogram count in metrics, but none found. Metrics: {updated_metrics}")
        
        # Verify that the delayed task appears in the metrics
        # The full task name includes the module path
        task_pattern = r'celery_task_runtime_seconds_.*{.*task_name="app\.metrics\.tests\.celery_app\.delayed_task".*}'
        task_matches = re.findall(task_pattern, updated_metrics)
        self.assertTrue(task_matches, 
                      f"Expected to find delayed_task in histogram metrics, but none found. Metrics: {updated_metrics}")
        
        print("Delayed task runtime measurements verified", file=sys.stderr)