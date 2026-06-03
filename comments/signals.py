from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import create_comment_on_post_notification
from comments.models import Comment


@receiver(post_save, sender=Comment)
def create_notification_for_comment_on_post(sender, instance, **kwargs):
    if kwargs.get("raw", False):
        return
    if not instance.is_approved:
        return
    create_comment_on_post_notification(instance)
