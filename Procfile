web: gunicorn app.core.wsgi:application
worker: celery -A app.core worker --loglevel=info
celery-exporter: celery-exporter --broker-url=$CLOUDAMQP_URL 