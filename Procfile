web: cd app && gunicorn core.wsgi:application
worker: cd app && celery -A core worker --loglevel=info
exporter: python -m app.metrics.run_exporter 