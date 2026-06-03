# File: comments/forms.py
import logging
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Comment, CommentTranslation

logger = logging.getLogger(__name__)

class CommentForm(forms.ModelForm):
    """
    🧠 A robust comment form with support for authenticated/anonymous users,
    threaded replies via 'parent', and bootstrap styling.
    """

    class Meta:
        model = Comment
        fields = ['content', 'parent', 'author_name', 'author_email']
        widgets = {
            'parent': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✏️ Bootstrap styling
        self.fields['content'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Write your comment here...')
        })
        self.fields['author_name'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Your Name (required)')
        })
        self.fields['author_email'].widget = forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Your Email (required, not published)')
        })

        # 🔐 Logic for authenticated users
        if self.user and self.user.is_authenticated:
            self.fields['author_name'].required = False
            self.fields['author_email'].required = False
            self.fields['author_name'].widget = forms.HiddenInput()
            self.fields['author_email'].widget = forms.HiddenInput()
            logger.debug(f"🧑‍💻 Customizing CommentForm for logged-in user: {self.user.username}")

    def clean(self):
        if self.errors:
            logger.warning(f"⚠️ CommentForm validation failed. Errors: {self.errors.as_json()}")
        return super().clean()


class CommentTranslationSuggestionForm(forms.ModelForm):
    class Meta:
        model = CommentTranslation
        fields = ["content"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget = forms.Textarea(
            attrs={
                "class": "form-control form-control-sm",
                "rows": 3,
                "placeholder": _("Suggest a better translation..."),
            }
        )
