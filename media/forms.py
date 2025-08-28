from django import forms
from .models import Media, Comment, Category

class MediaUploadForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Media
        fields = ['title', 'file', 'is_public', 'categories']
        labels = {'is_public': 'Make this media public?'}

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a public comment...'}),
        }
        labels = {
            'text': '' # Hide the label for the textarea
        }