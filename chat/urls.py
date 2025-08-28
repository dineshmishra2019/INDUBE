from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_room, name='chat_room'),
    path('chat/users/', views.users_list, name='chat_users_list'),
    path('chat/private/<int:user_id>/', views.private_chat_room, name='private_chat_room'),
    path('simple-chatbot/', views.simple_chatbot_view, name='simple_chatbot'),
    path('api/chat/', views.chat_api, name='chat_api'),
]