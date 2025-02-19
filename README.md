# Django Celery with Prometheus and Grafana Monitoring

This project demonstrates a Django application with Celery task queue, monitored using Prometheus and Grafana.

## Services

- Django application with Gunicorn (port 8787)
- RabbitMQ message broker
  - AMQP port: 5672
  - Management UI: http://localhost:15672 (guest/guest)
- Prometheus metrics (port 9999)
- Grafana dashboards (port 3333)
- Celery metrics exporter (port 9808)

## Quick Start

1. Start all services using the provided script:
```bash
./start.sh
```

This script:
- Kills any existing Gunicorn and Celery processes
- Starts Docker services (RabbitMQ, Prometheus, Grafana, Celery-exporter)
- Launches a Celery worker with 20 concurrent processes
- Starts Gunicorn with 2 workers and 2 threads per worker
- Sets up proper cleanup on exit

2. Generate sample tasks using the trigger script:
```bash
./trigger.sh
```

This script:
- Sends requests to the Django endpoint every second
- Each request triggers two Celery tasks (add and multiply)
- Continues until interrupted with Ctrl+C

## Monitoring

1. Access Grafana at the default dashboard: at http://localhost:3333/d/celery-metrics/celery-metrics?orgId=1 (login: admin/admin)
2. View raw metrics at http://localhost:9808/metrics from the Celery Exporter
3. Query metrics using Prometheus at http://localhost:9999

## Available Endpoints

- `/trigger/` - Triggers sample Celery tasks
- `/admin/` - Django admin interface

## Stopping Services

Press Ctrl+C in the terminal where `start.sh` is running. The script will:
- Kill Celery and Gunicorn processes
- Stop all Docker containers
- Clean up temporary files 