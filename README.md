# Django Celery Prometheus Monitoring

A demonstration project showing how to monitor Celery tasks using Prometheus and Grafana.

## Features

- Django web application with Celery tasks (no database required)
- Prometheus metrics collection via celery-exporter
- Grafana dashboards for task monitoring
- Test scripts for generating task patterns

The dashboard will have this stuff:
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
   - Service Ports:
     - `DJANGO_PORT`: Django application port (default: 8787)
     - `RABBITMQ_PORT`: RabbitMQ AMQP port (default: 5672)
     - `RABBITMQ_MANAGEMENT_PORT`: RabbitMQ management UI port (default: 15672)
     - `PROMETHEUS_PORT`: Prometheus port (default: 9999)
     - `GRAFANA_PORT`: Grafana port (default: 3333)
     - `CELERY_EXPORTER_PORT`: Celery exporter metrics port (default: 9808)
   - Celery Settings:
     - `CELERY_BROKER_URL`: RabbitMQ broker URL (default: amqp://guest:guest@localhost:5672//)

   Django and Celery will run on host machine directly, while prometheus, grafana and celery-exporter will run as docker containers.

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

![Grafana Dashboard](docs/dashboard.png)

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

### Automated Tests

The project includes comprehensive automated tests using pytest. To run all tests:

```bash
python -m pytest
```

Or to run tests with verbose output:

```bash
python -m pytest -v
```

#### Test Modules

1. **Metrics Exporter Tests** (`app/monitor/tests/test_exporter_redis.py`):
   - `test_task_success_metrics`: Verifies that successful task executions are correctly counted
   - `test_task_runtime_histogram`: Tests the histogram metrics for task runtime
   - `test_delayed_task_runtime`: Ensures delayed tasks have their runtime correctly measured
   - `test_periodic_updates`: Validates that metrics are updated at the configured interval rather than immediately
   - `test_received_and_failed_metrics`: Checks that received and failed task metrics are tracked properly

2. **Integration Tests** (`tests/test_integration.py`):
   - Tests the full integration between Django, Celery, and the metrics exporter
   - Verifies metrics are correctly exposed to Prometheus

### Manual Testing

The project includes a test script to generate various task patterns for manual testing:

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

### Testing Individual Components

To test specific components:

```bash
# Test only the Redis exporter
python -m pytest app/monitor/tests/test_exporter_redis.py

# Test a specific test case
python -m pytest app/monitor/tests/test_exporter_redis.py::TestCelerySuccessExporter::test_periodic_updates

# Test with coverage report
python -m pytest --cov=app
```

### Debugging Tests

For debugging tests, you can use the `-s` flag to see print statements:

```bash
python -m pytest -s app/monitor/tests/test_exporter_redis.py
```

## License

MIT License 