# File: menus/apps.py
from django.apps import AppConfig

class MenusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'menus'

    def ready(self):
        # This line is crucial. It tells Django to connect the signals
        # defined in menus/signals.py when the application starts.
        import menus.signals 