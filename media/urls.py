from django.urls import path
from . import views

urlpatterns = [
    # e.g., /
    path('', views.home, name='home'),
    # e.g., /category/travel/
    path('category/<slug:category_slug>/', views.home, name='home_by_category'),
    # e.g., /my-media/
    path('my-media/', views.my_media, name='my_media'),
    # e.g., /upload/
    path('upload/', views.upload_media, name='upload_media'),
    # e.g., /accounts/signup/
    path('accounts/signup/', views.signup, name='signup'),
    # e.g., /media/5/
    path('media/<int:pk>/', views.media_detail, name='media_detail'),
    # e.g., /media/5/delete/
    path('media/<int:pk>/delete/', views.delete_media, name='delete_media'),
    # e.g., /media/5/toggle-privacy/
    path('media/<int:pk>/toggle-privacy/', views.toggle_privacy, name='toggle_privacy'),
    # e.g., /media/5/like/
    path('media/<int:pk>/like/', views.like_media, name='like_media'),
]
