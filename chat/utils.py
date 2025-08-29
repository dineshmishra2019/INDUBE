import httpx
import json
import logging
from django.conf import settings
from langchain_community.chat_models import ChatOllama
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.schema import messages_from_dict, messages_to_dict

logger = logging.getLogger(__name__)

def get_ollama_models():
    """Fetches the list of available models from the Ollama API."""
    try:
        response = httpx.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5.0)
        response.raise_for_status()
        models_data = response.json().get('models', [])
        return [model['name'] for model in models_data]
    except (httpx.RequestError, json.JSONDecodeError):
        # Fallback to the default model if the API is unavailable
        return [settings.OLLAMA_MODEL]

async def get_ollama_response(message: str, model: str = None) -> str:
    """Gets a stateless response from the Ollama API."""
    if model is None:
        model = settings.OLLAMA_MODEL
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Using /api/chat for better prompt handling with some models
            response = await client.post(
                f"{settings.OLLAMA_HOST}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "stream": False
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get('message', {}).get('content', '').strip()

    except (httpx.RequestError, json.JSONDecodeError) as e:
        logger.error(f"Error calling Ollama API: {e}")
        return "Sorry, I'm having trouble connecting to the AI service."

# --- LangChain Integration ---

def get_conversation_chain(session, model_name: str):
    """
    Initializes a LangChain conversation chain, loading history from the session.
    """
    llm = ChatOllama(model=model_name, base_url=settings.OLLAMA_HOST)
    
    session_key = f"chat_history_{model_name}"
    
    # Load history from session
    history_dict = session.get(session_key, [])
    history_messages = messages_from_dict(history_dict)

    memory = ConversationBufferMemory(memory_key="history", return_messages=True)
    # Manually load history into memory
    memory.chat_memory.messages = history_messages

    prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(
                "You are a helpful and friendly AI assistant. Provide clear and concise answers."
            ),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ]
    )

    # LLMChain is a good general-purpose chain.
    chain = LLMChain(llm=llm, prompt=prompt, memory=memory, verbose=settings.DEBUG)
    return chain

def save_conversation_history(session, model_name: str, chain):
    """
    Saves the conversation history from the chain's memory into the session.
    """
    session_key = f"chat_history_{model_name}"
    history_messages = chain.memory.chat_memory.messages
    session[session_key] = messages_to_dict(history_messages)

def clear_conversation_history(session, model_name: str):
    """Clears the conversation history for a given model from the session."""
    session_key = f"chat_history_{model_name}"
    if session_key in session:
        del session[session_key]