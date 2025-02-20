web: gunicorn app.wsgi:application
worker: celery -A app worker --loglevel=info
celery-exporter: celery-exporter --broker=$CLOUDAMQP_URL 