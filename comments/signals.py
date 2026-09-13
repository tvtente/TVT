from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import (
    create_comment_on_post_notification,
    create_reply_to_comment_notification,
)
from comments.models import Comment


@receiver(post_save, sender=Comment)
def create_notification_for_comment_on_post(sender, instance, **kwargs):
    if kwargs.get("raw", False):
        return

    # The post author must know about a pending comment in order to moderate
    # it. Replies to other commenters remain private until approval.
    create_comment_on_post_notification(instance)
    if instance.is_approved:
        create_reply_to_comment_notification(instance)
