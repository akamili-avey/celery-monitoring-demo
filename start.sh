#!/bin/bash

echo "Starting services..."

# Kill existing gunicorn processes
pkill gunicorn
pkill celery

# Start Docker services
docker-compose up -d

# Wait for RabbitMQ
sleep 5

# Create project-specific temp directory
TMPDIR="$(pwd)/tmp/gunicorn"
mkdir -p "$TMPDIR"

# Start Celery worker and Gunicorn
cd app
# Start Celery with concurrency of 2 and memory limit
celery -A core worker --loglevel=info --events --concurrency=20 --max-memory-per-child=512000 &
CELERY_PID=$!

# Start Gunicorn with 2 workers and timeout settings
gunicorn core.wsgi:application \
    --bind 0.0.0.0:8787 \
    --workers 2 \
    --threads 2 \
    --worker-class=gthread \
    --worker-tmp-dir "$TMPDIR" \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30 \
    --graceful-timeout 30 &
GUNICORN_PID=$!

# Cleanup on exit
cleanup() {
    kill $CELERY_PID $GUNICORN_PID
    docker-compose down
    rm -rf "$TMPDIR"  # Clean up temp directory
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "
Services running:
- Django: http://localhost:8787
- RabbitMQ: http://localhost:5672 (AMQP), http://localhost:15672 (UI, guest/guest)
- Prometheus: http://localhost:9999
- Grafana: http://localhost:3333 (admin/admin)
- Metrics: http://localhost:9808/metrics

Press Ctrl+C to stop all services"

wait 