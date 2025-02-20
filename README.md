# Django Celery Prometheus Monitoring

A demonstration project showing how to monitor Celery tasks using Prometheus and Grafana.

## Features

- Django web application with Celery tasks
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

3. Start the services:
```bash
./start.sh
```

This will start:
- RabbitMQ (port 5672, management: 15672)
- Celery Exporter (port 9808)
- Prometheus (port 9999)
- Grafana (port 3333)
- Django application (port 8787)

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

## Development

To trigger test tasks manually:
```bash
curl "http://localhost:8787/trigger/?delay=0&failure=false"  # Successful task
curl "http://localhost:8787/trigger/?delay=2&failure=true"   # Failing task with delay
```

## Testing

The project includes test scripts to generate various task patterns:

1. Basic test pattern:
```bash
python tests/test_tasks.py
```
This runs a simple set of successful and failing tasks.

2. Advanced pattern test:
```bash
python tests/test_patterns.py
```
This runs a 3-minute test with different patterns:
- Steady rate of tasks
- Burst of tasks
- Mixed success/failure
- Tasks with delays
- Alternating success/failure
- Mixed delay burst

## License

MIT License 