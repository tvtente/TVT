from django.apps import AppConfig


class WidgetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'widgets'

    def ready(self):
        import widgets.signals  # Import the signals module to ensure it is registered
        # This will automatically connect the signals defined in widgets/signals.py
        # when the app is ready, allowing us to handle post_save and post_delete events.

        # Note: No need to import widget_tags here; they are loaded by Django's template system
        # when the template tags are used in templates.
        # The import here is only for signals, which handle cache invalidation.

        # If you have any other initialization code, you can add it here.
        # For example, you might want to register custom template tags or filters.
        # However, in this case, we are only concerned with signals for cache management.