from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Thread
from django.db.models import Count
from django.conf import settings
import httpx
import json
from django.http import JsonResponse
from .utils import get_ollama_response

def get_ollama_models():
    """Fetches the list of available models from the Ollama API."""
    try:
        response = httpx.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5.0)
        response.raise_for_status()
        models_data = response.json().get('models', [])
        return [model['name'] for model in models_data]
    except (httpx.RequestError, json.JSONDecodeError):
        return [settings.OLLAMA_MODEL]
@login_required
def chat_room(request):
    return render(request, 'chat/room.html')

@login_required
def users_list(request):
    """Lists users that can be chatted with."""
    users = User.objects.exclude(username=request.user.username)
    return render(request, 'chat/users.html', {'users': users})

@login_required
def private_chat_room(request, user_id):
    """A private chat room with a specific user."""
    other_user = get_object_or_404(User, id=user_id)

    # Find a thread that has exactly these two participants
    thread = Thread.objects.annotate(
        p_count=Count('participants')
    ).filter(
        p_count=2, participants=request.user
    ).filter(
        participants=other_user
    ).first()

    if not thread:
        thread = Thread.objects.create()
        thread.participants.add(request.user, other_user)

    # Load past messages
    messages = thread.messages.all()

    return render(request, 'chat/private_room.html', {'other_user': other_user, 'messages': messages})

@login_required
def simple_chatbot_view(request):
    """Renders the simple AJAX-based chatbot page."""
    context = {
        'available_models': get_ollama_models(),
        'default_model': settings.OLLAMA_MODEL,
    }
    return render(request, 'chat/simple_chatbot.html', context)

async def chat_api(request):
    """Handles API calls for the simple chatbot."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message')
            model = data.get('model', settings.OLLAMA_MODEL)
            reply = await get_ollama_response(message, model)
            return JsonResponse({'reply': reply, 'model': model})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)