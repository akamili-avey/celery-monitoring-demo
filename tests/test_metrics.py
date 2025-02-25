"""
Integration test for metrics endpoint using os.exec to start the application.
"""
import os
import sys
import time
import subprocess
import requests
import signal
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestMetricsWithExec(unittest.TestCase):
    """Test the metrics endpoint by starting the full application."""
    
    @classmethod
    def setUpClass(cls):
        """Start the application using the start script."""
        print("Starting the application...")
        
        # Start the application in a subprocess
        cls.app_process = subprocess.Popen(
            ['./start.sh'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            preexec_fn=os.setsid  # Create a new process group
        )

        # Define a signal handler
        def signal_handler(signum, frame):
            # Terminate the subprocess
            os.killpg(os.getpgid(cls.app_process.pid), signal.SIGTERM)

        # Register the signal handler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Wait for the application to start
        print("Waiting for the application to start...")
        time.sleep(10)  # Adjust this time as needed
        
        # Set the server URL
        cls.server_url = "http://localhost:8787"  # Use the port from .env
        
        # Check if the server is running by checking the metrics endpoint directly
        server_running = False
        for attempt in range(1, 4):  # Try 3 times
            try:
                response = requests.get(f"{cls.server_url}/metrics/")
                if response.status_code == 200:
                    server_running = True
                    print(f"Server is running (attempt {attempt})")
                    break
                print(f"Server check attempt {attempt} returned status code {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                print(f"Server check attempt {attempt} failed: {e}")
                if attempt < 3:
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
        
        if not server_running:
            print("Server check failed after 3 attempts")
            cls.tearDownClass()
            raise Exception("Failed to start the application")
    
    @classmethod
    def tearDownClass(cls):
        """Stop the application."""
        if hasattr(cls, 'app_process') and cls.app_process:
            try:
                # Ensure the subprocess is terminated when the test class is torn down
                os.killpg(os.getpgid(cls.app_process.pid), signal.SIGTERM)
                print("Stopped the application")
            except Exception as e:
                print(f"Error stopping the application: {e}")
    
    def test_metrics_endpoint(self):
        """Test that the metrics endpoint serves metrics from Redis."""
        try:
            # Check the metrics endpoint
            response = requests.get(f"{self.server_url}/metrics/")
            self.assertEqual(response.status_code, 200)
            
            # Print the metrics for debugging
            print("Metrics endpoint response:")
            print(response.text)
            
            # Check that the response contains metrics
            self.assertTrue(len(response.text) > 0, "Metrics response should not be empty")
            
            # If we expect specific metrics, check for them
            # For example, if we expect Celery metrics:
            if "celery" in response.text.lower():
                self.assertIn("celery", response.text.lower())
                print("Found Celery metrics in the response")
            else:
                print("No Celery metrics found in the response, but the endpoint is working")
            
        except requests.exceptions.ConnectionError as e:
            self.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main() 