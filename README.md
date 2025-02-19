# Django Celery Prometheus Monitoring

This project demonstrates how to monitor Celery tasks using Prometheus and Grafana in a Django application.

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the infrastructure services (RabbitMQ, Prometheus, Grafana):
```bash
docker-compose up -d
```

4. Run Django migrations:
```bash
cd app
python manage.py migrate
```

5. Start Django development server:
```bash
python manage.py runserver
```

6. In a new terminal, start Celery worker:
```bash
cd app
celery -A core worker -l info
```

## Testing

1. Trigger sample tasks:
```bash
curl http://localhost:8000/trigger/
```

2. View metrics:
```bash
curl http://localhost:8000/metrics/
```

## Monitoring

1. Access Prometheus UI: http://localhost:9090
2. Access Grafana UI: http://localhost:3000 (default credentials: admin/admin)

### Grafana Setup

1. Add Prometheus as a data source:
   - URL: http://prometheus:9090
   - Access: Browser

2. Import a dashboard for Celery metrics monitoring
   - Create a new dashboard
   - Add panels for:
     - Total tasks executed
     - Successful tasks
     - Failed tasks
     - Task execution rate 