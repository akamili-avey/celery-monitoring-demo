#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Using default values."
fi

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
# Start Celery with configured concurrency and memory limit
celery -A core worker --loglevel=info --events --concurrency=20 --max-memory-per-child=512000 &
CELERY_PID=$!

# Start Gunicorn with configured workers and timeout settings
gunicorn core.wsgi:application \
    --bind 0.0.0.0:${DJANGO_PORT:-8787} \
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
- Django: http://localhost:${DJANGO_PORT:-8787}
- RabbitMQ: http://localhost:${RABBITMQ_PORT:-5672} (AMQP), http://localhost:${RABBITMQ_MANAGEMENT_PORT:-15672} (UI, guest/guest)
- Prometheus: http://localhost:${PROMETHEUS_PORT:-9999}
- Grafana: http://localhost:${GRAFANA_PORT:-3333} (admin/admin)
- Metrics: http://localhost:${CELERY_EXPORTER_PORT:-9808}/metrics

Press Ctrl+C to stop all services"

wait 