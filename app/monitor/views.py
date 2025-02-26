"""
Views for metrics endpoints.
"""
import os
import redis
import base64
from functools import wraps
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.conf import settings

# Get Redis URL from settings or environment
REDIS_URL = getattr(settings, 'REDIS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
METRICS_KEY = 'celery_metrics'

# Simplified decorator with empty defaults since we pass values explicitly when using it
def basic_auth_required(auth_user='', auth_pass=''):
    """
    Decorator that enforces HTTP Basic Authentication for a view.
    
    Args:
        auth_user (str, optional): Username for authentication. Defaults to empty string.
        auth_pass (str, optional): Password for authentication. Defaults to empty string.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip authentication if credentials are not configured
            if not auth_user or not auth_pass:
                return view_func(request, *args, **kwargs)
            
            # Check for authorization header
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if not auth_header.startswith('Basic '):
                return HttpResponse(
                    'Unauthorized: Basic authentication required',
                    status=401,
                    headers={'WWW-Authenticate': 'Basic realm="Metrics Authentication"'}
                )
            
            try:
                # Decode the base64 credentials
                auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = auth_decoded.split(':', 1)
                
                # Check if credentials match
                if username == auth_user and password == auth_pass:
                    return view_func(request, *args, **kwargs)
            except Exception:
                pass
            
            # If we get here, authentication failed
            return HttpResponse(
                'Unauthorized: Invalid credentials',
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="Metrics Authentication"'}
            )
        
        return wrapper
    return decorator

@require_GET
# Example of passing environment variables directly in the decorator
@basic_auth_required(
    auth_user=os.getenv('PROMETHEUS_METRICS_ENDPOINT_AUTH_USERNAME', ''),
    auth_pass=os.getenv('PROMETHEUS_METRICS_ENDPOINT_AUTH_PASSWORD', '')
)
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