from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Thread
from django.db.models import Count
from django.conf import settings
import json
from django.http import JsonResponse
from .utils import get_ollama_models, get_ollama_response, get_conversation_chain, save_conversation_history, clear_conversation_history
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)
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

def public_chatbot_view(request):
    """Renders the public AJAX-based chatbot page that does not require login."""
    context = {
        'available_models': get_ollama_models(),
        'default_model': settings.OLLAMA_MODEL,
    }
    return render(request, 'chat/public_chatbot.html', context)

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

@login_required
def ai_chat_view(request):
    """Renders the dedicated AI chat page that uses LangChain."""
    context = {
        'available_models': get_ollama_models(),
        'default_model': settings.OLLAMA_MODEL,
    }
    return render(request, 'chat/ai_chat.html', context)

@login_required
async def ai_chat_api(request):
    """Handles API calls for the LangChain-powered chatbot with conversation history."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        model = data.get('model', settings.OLLAMA_MODEL)
        action = data.get('action')

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Handle clearing history
    if action == 'clear':
        await sync_to_async(clear_conversation_history)(request.session, model)
        return JsonResponse({'status': 'history cleared'})

    # Handle sending a message
    message = data.get('message')
    if not message:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    try:
        # Get chain with history from session
        chain = await sync_to_async(get_conversation_chain)(request.session, model)
        
        # Run the prediction (blocking I/O) in a separate thread
        response = await sync_to_async(chain.predict)(input=message)

        # Save the updated history back to the session
        await sync_to_async(save_conversation_history)(request.session, model, chain)

        return JsonResponse({'reply': response, 'model': model})
    except Exception as e:
        logger.error(f"Error in AI chat API: {e}", exc_info=True)
        return JsonResponse({'error': 'An error occurred while processing your request.'}, status=500)