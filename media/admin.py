from django.contrib import admin
from .models import Media, Comment, Like, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'uploaded_at', 'is_public')
    list_filter = ('is_public', 'owner', 'categories')

admin.site.register(Comment)
admin.site.register(Like)