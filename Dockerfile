FROM python:3.9-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "core", "worker", "--loglevel=info"] 