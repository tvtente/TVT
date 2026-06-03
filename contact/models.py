from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User 

class ContactMessage(models.Model):
    """
    Represents a message submitted through the site's contact form.
    """
    
    # An enumeration for message priority levels.
    # This is the modern, recommended way to create choices in Django.
    class Priority(models.IntegerChoices):
        LOW = 1, _('Low')
        MEDIUM = 2, _('Medium')
        HIGH = 3, _('High')
        URGENT = 4, _('Urgent')
        CRITICAL = 5, _('Critical')

    # Fields for the submitted message content
    name = models.CharField(max_length=150, verbose_name=_("Name"))
    email = models.EmailField(verbose_name=_("Email"))
    subject = models.CharField(max_length=200, verbose_name=_("Subject"))
    message = models.TextField(verbose_name=_("Message"))
    
    # Fields for internal management
    priority = models.IntegerField(
        choices=Priority.choices, 
        default=Priority.MEDIUM,
        verbose_name=_("Priority")
    )
    is_read = models.BooleanField(
        default=False, 
        verbose_name=_("Has been read?"),
        help_text=_("Indicates if an admin has reviewed this message.")
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("Received At")
    )
    responded_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_("Responded At"),
        help_text=_("Automatically set when the message is first marked as read.")
    )
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # Don't delete the message if the user is deleted
        null=True, # this field can be empty if no admin has responded yet
        blank=True,
        related_name='handled_contact_messages',
        verbose_name=_("Responded By")
    )
    class Meta:
        # Default ordering puts the most important and newest messages at the top.
        ordering = ['-priority', '-created_at']
        verbose_name = _("Contact Message")
        verbose_name_plural = _("Contact Messages")

    def __str__(self):
        return f'Message from {self.name} - "{self.subject}"'