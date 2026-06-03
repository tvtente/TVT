from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import create_followed_author_post_notifications
from posts.models import Post


PostTranslation = Post._parler_meta.root_model


@receiver(post_save, sender=Post)
def create_notifications_for_published_post(sender, instance, **kwargs):
    if kwargs.get("raw", False):
        return
    create_followed_author_post_notifications(instance)


@receiver(post_save, sender=PostTranslation)
def create_notifications_for_published_post_translation(sender, instance, **kwargs):
    if kwargs.get("raw", False):
        return
    create_followed_author_post_notifications(instance.master)
