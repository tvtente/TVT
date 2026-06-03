# contact/admin.py
import logging
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import ContactMessage

logger = logging.getLogger(__name__)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """ Admin options for the ContactMessage model. """
    list_display = ('subject', 'name', 'priority', 'is_read', 'responded_by', 'responded_at')
    list_filter = ('is_read', 'priority', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    list_editable = ('is_read', 'priority')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at', 'responded_at', 'responded_by')

    def save_model(self, request, obj, form, change):
        """
        Custom save logic: sets 'responded_at' timestamp and 'responded_by' user
        when a message is first marked as read, and clears them if marked as unread.
        """
        # Check if 'is_read' is among the fields that have been changed in the form.
        if 'is_read' in form.changed_data:
            # Case 1: The message is being marked as READ.
            if obj.is_read:
                # We only set the data the first time it's marked as read.
                if not obj.responded_at:
                    obj.responded_at = timezone.now()
                    obj.responded_by = request.user
                    logger.info(
                        f"Admin user '{request.user.username}' (ID: {request.user.id}) marked "
                        f"contact message ID {obj.id} ('{obj.subject}') as READ."
                    )
            # Case 2: The message is being marked as UNREAD.
            else:
                obj.responded_at = None
                obj.responded_by = None
                logger.info(
                    f"Admin user '{request.user.username}' (ID: {request.user.id}) marked "
                    f"contact message ID {obj.id} as UNREAD."
                )
        # Call the original save_model method to continue the saving process.
        super().save_model(request, obj, form, change)