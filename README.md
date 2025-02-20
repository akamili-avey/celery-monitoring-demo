# Django Celery Prometheus Monitoring

A demonstration project showing how to monitor Celery tasks using Prometheus and Grafana.

## Features

- Django web application with Celery tasks (no database required)
- Prometheus metrics collection via celery-exporter
- Grafana dashboards for task monitoring
- Test scripts for generating task patterns
- Real-time monitoring of task success/failure rates
- Task latency tracking
- Customizable alert rules and notifications
- Failure rate threshold alerts

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- virtualenv

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the `.env.example` file to `.env`:

   ```bash
   cp .env.example .env
   ```

4. Configure your environment variables in `.env`. The following variables are available:
   - Django Settings:
     - `DJANGO_SECRET_KEY`: Django secret key
     - `DJANGO_DEBUG`: Debug mode (True/False)
     - `DJANGO_ALLOWED_HOSTS`: Comma-separated list of allowed hosts
     - `DJANGO_HOST`: Host for the Django application
   - Service Ports:
     - `DJANGO_PORT`: Django application port (default: 8787)
     - `RABBITMQ_PORT`: RabbitMQ AMQP port (default: 5672)
     - `RABBITMQ_MANAGEMENT_PORT`: RabbitMQ management UI port (default: 15672)
     - `PROMETHEUS_PORT`: Prometheus port (default: 9999)
     - `GRAFANA_PORT`: Grafana port (default: 3333)
     - `CELERY_EXPORTER_PORT`: Celery exporter metrics port (default: 9808)
   - Celery Settings:
     - `CELERY_BROKER_URL`: RabbitMQ broker URL
     - `CELERY_WORKERS`: Number of Celery workers
     - `CELERY_MAX_MEMORY`: Maximum memory per child in KB
   - Gunicorn Settings:
     - `GUNICORN_WORKERS`: Number of Gunicorn workers
     - `GUNICORN_THREADS`: Number of threads per worker
     - `GUNICORN_MAX_REQUESTS`: Maximum requests per worker
     - `GUNICORN_MAX_REQUESTS_JITTER`: Random jitter for max requests
     - `GUNICORN_TIMEOUT`: Worker timeout in seconds
     - `GUNICORN_GRACEFUL_TIMEOUT`: Graceful shutdown timeout

5. Start all services using the provided script:

   ```bash
   ./start.sh
   ```

This will start:
- RabbitMQ (AMQP and management interface)
- Celery Exporter for metrics collection
- Prometheus for metrics storage
- Grafana for visualization
- Django application with Celery workers

## Monitoring & Alerts
Open this as we run the testing scripts.

1. Access Grafana at http://localhost:3333 (admin/admin)
2. The default dashboard shows:
   - Task execution rate
   - Total tasks executed
   - Successful tasks
   - Failed tasks
   - Task failure rate
   - Task P95 latency

### Configured Alerts:

1. High Failure Rate Alert
   - Triggers when task failure rate exceeds 20% over 1 minute
   - Severity: Warning at 20%, Critical at 50%
   - Evaluation: Every 1 minute

2. Task Latency Alert
   - Triggers when P95 latency exceeds 10 seconds
   - Severity: Warning
   - Evaluation: Every 1 minute

3. Queue Size Alert
   - Triggers when task queue size exceeds 100 tasks
   - Severity: Warning at 100, Critical at 500
   - Evaluation: Every 1 minute

To test alerts:
```bash
# Generate high failure rate
curl "http://localhost:8787/trigger/?delay=0&failure=true"

# Generate high latency
curl "http://localhost:8787/trigger/?delay=15&failure=false"
```

## Metrics

The following metrics are collected:
- `celery_task_received_total`: Total tasks received
- `celery_task_succeeded_total`: Successfully completed tasks
- `celery_task_failed_total`: Failed tasks
- `celery_task_runtime_seconds`: Task execution time

## Testing

The project includes test scripts to generate various task patterns:

1. Basic test pattern:
```bash
python tests/test_tasks.py
```
This runs a simple set of:
- 5 successful tasks
- 3 delayed tasks (2-second delay)
- 2 failing tasks

2. Advanced pattern test:
```bash
python tests/test_patterns.py
```
This runs a 3-minute test with different patterns:
- Phase 1 (0-30s): Steady rate of successful tasks (1 every 5s)
- Phase 2 (30-60s): Burst of 10 tasks in quick succession
- Phase 3 (60-90s): Mix of random success/failure tasks
- Phase 4 (90-120s): Quiet period followed by delayed tasks
- Phase 5 (120-150s): Alternating success/failure tasks
- Phase 6 (150-180s): Final burst with random delays

## License

MIT License 