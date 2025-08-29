import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
from django.db.models import Count
from django.conf import settings
from .models import Thread, Message
from .utils import get_conversation_chain, save_conversation_history
import logging

logger = logging.getLogger(__name__)
class ChatConsumer(AsyncWebsocketConsumer):
    """Handles WebSocket connections for the public chat room."""
    # This set is shared across all ChatConsumer instances in the same process.
    # For a multi-process setup, a shared backend like Redis would be needed.
    online_users = set()

    async def connect(self):
        self.room_name = 'public_chat'
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Add user to the online set and broadcast the updated user list
        ChatConsumer.online_users.add(self.user.username)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_list_update',
                'users': sorted(list(ChatConsumer.online_users))
            }
        )

    async def disconnect(self, close_code):
        # Remove user from the online set and broadcast the updated list
        if self.user.is_authenticated:
            ChatConsumer.online_users.discard(self.user.username)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_list_update',
                    'users': sorted(list(ChatConsumer.online_users))
                }
            )

        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Receives a message from the WebSocket.
        If the message starts with '@bot', it's treated as a query for the AI.
        Otherwise, it's broadcast to the entire room.
        """
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
        except (json.JSONDecodeError, KeyError):
            logger.warning("ChatConsumer received malformed data: %s", text_data)
            return

        username = self.user.username
        
        if message.strip().lower().startswith('@bot '):
            query = message.strip()[5:]

            # Echo the user's query back to them so it appears in their log
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': message,
                'username': username
            }))

            # Use LangChain for a stateful conversation
            session = self.scope['session']
            model = settings.OLLAMA_MODEL
            try:
                chain = await sync_to_async(get_conversation_chain)(session, model)
                response = await sync_to_async(chain.predict)(input=query)
                await sync_to_async(save_conversation_history)(session, model, chain)

                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': response,
                    'username': f'AI Assistant ({model})'
                }))
            except Exception as e:
                logger.error(f"Error in ChatConsumer with LangChain: {e}", exc_info=True)
                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': "Sorry, I had a problem processing that.",
                    'username': 'AI Assistant'
                }))
        else:
            # Broadcast the message to the room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username
                }
            )

    async def chat_message(self, event):
        """Receives a message from the room group and sends it to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username']
        }))

    async def user_list_update(self, event):
        """Receives a user list update and sends it to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'user_list',
            'users': event['users']
        }))

@sync_to_async
def get_thread(user1, user2_id):
    user2 = User.objects.get(id=user2_id)
    # Correctly find a thread with exactly two participants
    thread = Thread.objects.annotate(
        p_count=Count('participants')
    ).filter(
        p_count=2, participants=user1
    ).filter(
        participants=user2
    ).first()
    if not thread:
        thread = Thread.objects.create()
        thread.participants.add(user1, user2)
    return thread

@sync_to_async
def save_message(thread, sender, text):
    return Message.objects.create(thread=thread, sender=sender, text=text)

class PrivateChatConsumer(AsyncWebsocketConsumer):
    """Handles WebSocket connections for private one-on-one chats."""
    async def connect(self):
        self.user = self.scope['user']
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']

        if not self.user.is_authenticated:
            await self.close()
            return

        user_ids = sorted([self.user.id, int(self.other_user_id)])
        self.room_group_name = f'private_chat_{user_ids[0]}_{user_ids[1]}'
        self.thread = await get_thread(self.user, self.other_user_id)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
        except (json.JSONDecodeError, KeyError):
            logger.warning("PrivateChatConsumer received malformed data: %s", text_data)
            return

        username = self.user.username

        if message.strip().lower().startswith('@bot '):
            query = message.strip()[5:]

            # Echo the user's query back to them so it appears in their log
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': message,
                'username': username
            }))

            # Use LangChain for a stateful conversation, private to the user
            session = self.scope['session']
            model = settings.OLLAMA_MODEL
            try:
                chain = await sync_to_async(get_conversation_chain)(session, model)
                response = await sync_to_async(chain.predict)(input=query)
                await sync_to_async(save_conversation_history)(session, model, chain)

                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': response,
                    'username': f'AI Assistant ({model})'
                }))
            except Exception as e:
                logger.error(f"Error in PrivateChatConsumer with LangChain: {e}", exc_info=True)
                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': "Sorry, I had a problem processing that.",
                    'username': 'AI Assistant'
                }))
        else:
            # It's a regular message for the other user; save and broadcast it.
            await save_message(self.thread, self.user, message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'chat_message', 'message': message, 'username': username}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'], 'username': event['username']
        }))