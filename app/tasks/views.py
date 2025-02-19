from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .tasks import add

# Create your views here.

@csrf_exempt
def trigger_task(request):
    """Endpoint to trigger sample tasks."""
    # Get parameters from request with defaults
    delay = float(request.GET.get('delay', 0))
    failure = request.GET.get('failure', '').lower() == 'true'
    
    # Trigger tasks with parameters
    add.delay(4, 4, delay=delay, failure=failure)
    
    return JsonResponse({
        "message": "Tasks triggered successfully",
        "parameters": {
            "delay": delay,
            "failure": failure
        }
    })
