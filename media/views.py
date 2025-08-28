from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import Media, Like, Comment, Category
from .forms import MediaUploadForm, CommentForm
from django.http import Http404
from django.core.exceptions import PermissionDenied

def home(request, category_slug=None):
    """
    Displays all public media items, optionally filtered by category.
    """
    categories = Category.objects.all()
    public_media = Media.objects.filter(is_public=True)

    current_category = None
    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        public_media = public_media.filter(categories=current_category)

    public_media = public_media.order_by('-uploaded_at')

    context = {
        'media_items': public_media,
        'categories': categories,
        'current_category': current_category,
    }
    return render(request, 'media/home.html', context)

@login_required
def my_media(request):
    """
    Displays all media items owned by the currently logged-in user.
    """
    user_media = Media.objects.filter(owner=request.user).order_by('-uploaded_at')
    return render(request, 'media/my_media.html', {'media_items': user_media})

def signup(request):
    """
    Handles user registration.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log the user in after signing up
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def upload_media(request):
    """
    Handles file uploads.
    """
    if request.method == 'POST':
        form = MediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            media_instance = form.save(commit=False)
            media_instance.owner = request.user
            media_instance.save()
            return redirect('my_media')
    else:
        form = MediaUploadForm()
    return render(request, 'media/upload.html', {'form': form})

def media_detail(request, pk):
    """
    Displays a single media item, its comments, and handles new comment submission.
    Enforces privacy rules: only owner can see private media.
    """
    media_item = get_object_or_404(Media, pk=pk)
    comments = media_item.comments.select_related('author').all()
    comment_form = CommentForm()

    # Check for permissions
    if not media_item.is_public and media_item.owner != request.user:
        # This raises a 404 error, hiding the existence of the private item.
        raise Http404

    # Handle new comment submission
    if request.method == 'POST' and request.user.is_authenticated and 'text' in request.POST:
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.media = media_item
            new_comment.author = request.user
            new_comment.save()
            return redirect('media_detail', pk=pk) # Redirect to the same page to prevent form resubmission

    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = Like.objects.filter(media=media_item, user=request.user).exists()

    context = {
        'item': media_item,
        'comments': comments,
        'comment_form': comment_form,
        'user_has_liked': user_has_liked,
    }
    return render(request, 'media/media_detail.html', context)

@login_required
def delete_media(request, pk):
    """
    Deletes a media item. Only the owner can perform this action.
    """
    media_item = get_object_or_404(Media, pk=pk)

    if media_item.owner != request.user:
        # If the user is not the owner, deny permission.
        raise PermissionDenied

    if request.method == 'POST':
        # Delete the file from storage
        media_item.file.delete(save=False)
        # Delete the database record
        media_item.delete()
        return redirect('my_media')

    # If it's a GET request, just show the detail page (or a confirmation page)
    return redirect('media_detail', pk=pk)

@login_required
def toggle_privacy(request, pk):
    """
    Toggles the is_public status of a media item.
    Only the owner can perform this action and only via a POST request.
    """
    media_item = get_object_or_404(Media, pk=pk)

    if media_item.owner != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        media_item.is_public = not media_item.is_public
        media_item.save()

    return redirect('media_detail', pk=pk)

@login_required
def like_media(request, pk):
    """
    Handles liking or unliking a media item.
    """
    media_item = get_object_or_404(Media, pk=pk)
    if request.method == 'POST':
        like, created = Like.objects.get_or_create(media=media_item, user=request.user)
        if not created:
            # The like already existed, so we delete it (unlike)
            like.delete()
    return redirect('media_detail', pk=pk)
