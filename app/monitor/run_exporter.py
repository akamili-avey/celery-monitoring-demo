#!/usr/bin/env python
"""
Script to run the Celery Success Exporter.
"""
import os
import sys
import time
import signal
import ssl
from app.monitor.exporter import CelerySuccessExporter

def main():
    """Run the Celery Success Exporter."""
    # Get configuration from environment variables
    broker_url = os.environ.get('CELERY_BROKER_URL')
    redis_url = os.environ.get('REDIS_URL')
    update_interval = float(os.environ.get('EXPORTER_UPDATE_INTERVAL', '0.5'))
    
    if not broker_url:
        print("Error: CELERY_BROKER_URL environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not redis_url:
        print("Error: REDIS_URL environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Handle SSL certificate verification for Redis
    if redis_url.startswith('rediss://'):
        print("Using Redis with SSL, disabling certificate verification", file=sys.stderr)
        # Modify the URL to include SSL parameters
        redis_url = redis_url + '?ssl_cert_reqs=none'
    
    print(f"Starting Celery Success Exporter with broker={broker_url}, redis={redis_url}", file=sys.stderr)
    
    # Create and start the exporter
    exporter = CelerySuccessExporter(
        broker_url=broker_url,
        redis_url=redis_url,
        update_interval=update_interval
    )
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("Received shutdown signal, stopping exporter...", file=sys.stderr)
        exporter.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the exporter
    exporter.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received, stopping exporter...", file=sys.stderr)
        exporter.stop()

if __name__ == "__main__":
    main() 