import json
import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

async def get_ollama_response(message, model_name=None):
    """Sends a message to the Ollama API and gets a response."""
    if model_name is None:
        model_name = settings.OLLAMA_MODEL

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OLLAMA_HOST}/api/chat",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": message}],
                    "stream": False, # Use non-streaming for simplicity
                },
                timeout=60.0, # Increased timeout for model generation
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data.get('message', {}).get('content', '')
    except (httpx.RequestError, json.JSONDecodeError, KeyError) as e:
        error_message = f"Could not get a response from Ollama: {e}"
        logger.error(error_message)
        return "Sorry, I'm having trouble thinking right now. Please check if Ollama is running."