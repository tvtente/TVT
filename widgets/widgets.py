# File: widgets/widgets.py
from django import forms

class CustomClearableFileInput(forms.ClearableFileInput):
    """
    A custom file input widget that uses a specific template
    to provide full control over its HTML rendering.
    """
    # This tells Django to use our custom HTML file to render this widget.
    template_name = 'widgets/custom_clearable_file_input.html'