from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import os

class Category(models.Model):
    """Represents a category for media files."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Media(models.Model):
    """
    Represents an uploaded image or video file.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_items')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='user_media/')
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(Category, related_name='media_files', blank=True)

    @property
    def is_image(self):
        """Checks if the file is an image based on its extension."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(self.file.name)[1]
        return ext.lower() in image_extensions

    @property
    def like_count(self):
        """Returns the total number of likes for this media item."""
        return self.likes.count()

    def __str__(self):
        return f'"{self.title}" by {self.owner.username}'

class Comment(models.Model):
    """
    Represents a comment on a media item.
    """
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.media.title}'

class Like(models.Model):
    """
    Represents a user's like on a media item.
    """
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        # Ensures a user can only like a media item once
        unique_together = ('media', 'user')

    def __str__(self):
        return f'{self.user.username} likes {self.media.title}'