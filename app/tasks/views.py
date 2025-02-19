from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .tasks import add, multiply

# Create your views here.

@csrf_exempt
def trigger_task(request):
    """Endpoint to trigger sample tasks."""
    # Trigger both tasks
    add.delay(4, 4)
    multiply.delay(4, 4)
    
    return JsonResponse({
        "message": "Tasks triggered successfully"
    })
