# contact/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    """
    A form for users to send contact messages.
    It's based on the ContactMessage model.
    """
    class Meta:
        model = ContactMessage
        # These are the fields the user will see and fill out.
        # We exclude fields like 'is_read' or 'priority' which are for admin use only.
        fields = ['name', 'email', 'subject', 'message']

        # Here we can add Bootstrap classes and other attributes to our form fields.
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': _('Your Full Name')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': _('Your Email Address')
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': _('Message Subject')
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'placeholder': _('Write your message here...')
            }),
        }

        # Optional: Customize the labels if needed.
        # By default, Django uses the verbose_name from the model.
        labels = {
            'name': _('Full Name'),
            'email': _('Email Address'),
        }