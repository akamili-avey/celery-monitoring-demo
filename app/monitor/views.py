"""
Views for metrics endpoints.
"""
import os
import redis
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.conf import settings

# Get Redis URL from settings or environment
REDIS_URL = getattr(settings, 'REDIS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
METRICS_KEY = 'celery_metrics'

@require_GET
def metrics_view(request):
    """
    Endpoint that serves Prometheus metrics from Redis.
    """
    # Connect to Redis with SSL certificate handling
    redis_url = REDIS_URL
    if redis_url.startswith('rediss://'):
        # Add SSL certificate verification parameter for secure Redis connections
        if '?' not in redis_url:
            redis_url += '?ssl_cert_reqs=none'
        else:
            redis_url += '&ssl_cert_reqs=none'
    
    try:
        # Connect to Redis
        redis_client = redis.Redis.from_url(redis_url)
        
        # Get metrics from Redis
        metrics_data = redis_client.get(METRICS_KEY)
        
        if not metrics_data:
            return HttpResponse(
                "# No metrics available\n",
                content_type="text/plain"
            )
        
        # Return metrics as plain text
        return HttpResponse(
            metrics_data,
            content_type="text/plain"
        )
    except Exception as e:
        # Log the error and return a meaningful error message
        error_message = f"Error connecting to Redis: {str(e)}"
        return HttpResponse(
            f"# Error: {error_message}\n",
            content_type="text/plain",
            status=500
        ) 