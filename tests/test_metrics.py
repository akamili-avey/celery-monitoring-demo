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
        
        # Wait for the application to start
        print("Waiting for the application to start...")
        time.sleep(10)  # Adjust this time as needed
        
        # Set the server URL
        cls.server_url = "http://localhost:8787"  # Use the port from .env
        
        # Check if the server is running
        server_running = False
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(f"{cls.server_url}/metrics/")
                if response.status_code == 200:
                    print(f"Server is running (attempt {attempt})")
                    server_running = True
                    break
                print(f"Server check attempt {attempt} returned status code {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                print(f"Server check attempt {attempt} failed: {e}")
                
            if attempt < max_attempts:
                print(f"Retrying in 2 seconds... (attempt {attempt}/{max_attempts})")
                time.sleep(2)
        
        # If the server failed to start, clean up and raise an exception
        if not server_running:
            cls.tearDownClass()
            raise Exception("Failed to start the application")
    
    @classmethod
    def tearDownClass(cls):
        """Stop the application."""
        if hasattr(cls, 'app_process') and cls.app_process:
            try:
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
            
            # Check that the response contains metrics
            self.assertTrue(len(response.text) > 0, "Metrics response should not be empty")
            
            # Check for expected metrics content
            # This is a basic check - you may want to add more specific assertions
            # based on what metrics you expect to see
            if "celery" in response.text.lower():
                self.assertIn("celery", response.text.lower())
            
        except requests.exceptions.ConnectionError as e:
            self.fail(f"Failed to connect to server: {e}")
        except Exception as e:
            self.fail(f"Test failed: {e}")

if __name__ == '__main__':
    unittest.main() 