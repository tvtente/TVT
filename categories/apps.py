# File: categories/apps.py
from django.apps import AppConfig

class CategoriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'categories'

    def ready(self):
        # This imports the signals so they are connected when Django starts.
        import categories.signals