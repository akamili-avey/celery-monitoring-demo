web: cd app && gunicorn core.wsgi:application
worker: cd app && celery -A core worker --loglevel=info
celery-exporter: celery-exporter --broker-url=$CLOUDAMQP_URL 