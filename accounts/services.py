import logging
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from accounts.models import UserFollow, UserNotification


User = get_user_model()
# Use the Django logger namespace so SMTP failures reach the configured
# rotating error log in every deployed environment.
logger = logging.getLogger("django.accounts.notifications")


def _absolute_notification_url(url):
    if not url:
        return settings.PUBLIC_SITE_URL
    if url.startswith(("https://", "http://")):
        return url
    return urljoin(f"{settings.PUBLIC_SITE_URL.rstrip('/')}/", url.lstrip("/"))


def send_notification_email(notification):
    """Deliver a concise, non-blocking email for a newly created notification."""
    if not getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False):
        notification.email_delivery_status = UserNotification.EmailDeliveryStatus.SKIPPED
        notification.email_error = "Email notifications are disabled by configuration."
        notification.save(update_fields=["email_delivery_status", "email_error"])
        logger.warning("Notification email skipped because notifications are disabled: %s", notification.id)
        return False

    recipient_email = (getattr(notification.recipient, "email", "") or "").strip()
    if not recipient_email:
        notification.email_delivery_status = UserNotification.EmailDeliveryStatus.SKIPPED
        notification.email_error = "The recipient has no email address."
        notification.save(update_fields=["email_delivery_status", "email_error"])
        logger.warning("Notification email skipped because recipient has no email: %s", notification.id)
        return False

    notification_url = _absolute_notification_url(notification.url)
    body = "\n\n".join(
        [
            notification.message,
            gettext("Open the notification:") + f" {notification_url}",
            gettext("You receive this email because of activity in your TVTente account."),
        ]
    )

    def deliver():
        try:
            send_mail(
                subject=f"[TVTente] {notification.title}",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
        except Exception as exc:
            # A mail provider outage must never prevent comments or follows.
            notification.email_delivery_status = UserNotification.EmailDeliveryStatus.FAILED
            notification.email_error = str(exc)[:2000]
            notification.save(update_fields=["email_delivery_status", "email_error"])
            logger.exception(
                "Could not send notification email to user %s (notification %s)",
                notification.recipient_id,
                notification.id,
            )
        else:
            notification.email_delivery_status = UserNotification.EmailDeliveryStatus.SENT
            notification.email_sent_at = timezone.now()
            notification.email_error = ""
            notification.save(
                update_fields=["email_delivery_status", "email_sent_at", "email_error"]
            )
            logger.info("Notification email sent: %s", notification.id)

    transaction.on_commit(deliver)
    return True


def get_user_display_name(user):
    if not user:
        return ""
    profile = getattr(user, "profile", None)
    if profile is not None:
        display_name = profile.get_display_name()
        if display_name:
            return display_name
    return user.get_full_name() or user.username


def create_notification(
    *,
    recipient,
    notification_type,
    title,
    message,
    actor=None,
    url="",
    related_post=None,
    payload=None,
    dedupe_key="",
):
    payload = payload or {}

    if dedupe_key:
        existing = UserNotification.objects.filter(
            recipient=recipient,
            dedupe_key=dedupe_key,
        ).first()
        if existing:
            return existing, False

    notification = UserNotification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        url=url,
        related_post=related_post,
        payload=payload,
        dedupe_key=dedupe_key,
    )
    return notification, True


def create_followed_author_post_notifications(post):
    if post.status != "published":
        return 0

    post_title = post.safe_translation_getter("title", any_language=True)
    post_slug = post.safe_translation_getter("slug", any_language=True)
    if not post_title or not post_slug:
        return 0

    actor_name = get_user_display_name(post.author)
    post_url = post.get_absolute_url()
    follower_ids = UserFollow.objects.filter(
        followed=post.author,
    ).values_list("follower_id", flat=True)

    created_count = 0
    for recipient in User.objects.filter(id__in=follower_ids):
        _, created = create_notification(
            recipient=recipient,
            actor=post.author,
            notification_type=UserNotification.NotificationType.FOLLOWED_AUTHOR_PUBLISHED_POST,
            title=gettext("New post from %(user)s") % {"user": actor_name},
            message=gettext('%(user)s published the post "%(title)s".')
            % {
                "user": actor_name,
                "title": post_title,
            },
            url=post_url,
            related_post=post,
            payload={
                "post_id": post.id,
                "post_title": post_title,
                "author_username": post.author.username,
            },
            dedupe_key=f"followed-post:{post.id}:{recipient.id}",
        )
        if created:
            created_count += 1

    return created_count


def create_comment_on_post_notification(comment):
    post = comment.post
    recipient = getattr(post, "author", None)
    if recipient is None:
        return 0

    actor = getattr(comment, "user", None)
    if actor is not None and actor == recipient:
        return 0

    if actor is not None:
        actor_name = get_user_display_name(actor)
    else:
        actor_name = comment.author_name or gettext("Someone")

    post_title = post.safe_translation_getter("title", any_language=True) or ""
    if comment.is_approved:
        title = gettext("New comment on your post")
        message = gettext('%(user)s commented on your post "%(title)s".') % {
            "user": actor_name,
            "title": post_title,
        }
    else:
        title = gettext("New comment awaiting review")
        message = gettext('%(user)s commented on "%(title)s" and it is awaiting review.') % {
            "user": actor_name,
            "title": post_title,
        }

    notification, created = create_notification(
        recipient=recipient,
        actor=actor,
        notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
        title=title,
        message=message,
        url=post.get_absolute_url(),
        related_post=post,
        payload={
            "comment_id": comment.id,
            "post_id": post.id,
            "post_title": post_title,
            "actor_name": actor_name,
            "is_approved": comment.is_approved,
        },
        dedupe_key=f"comment-on-post:{comment.id}:{recipient.id}",
    )
    if created:
        send_notification_email(notification)
    return 1 if created else 0


def create_reply_to_comment_notification(comment):
    """Notify the registered author of a parent comment about a reply."""
    parent = getattr(comment, "parent", None)
    recipient = getattr(parent, "user", None) if parent else None
    if recipient is None:
        return 0

    actor = getattr(comment, "user", None)
    if actor is not None and actor == recipient:
        return 0

    # The post author already receives a comment notification.
    if recipient == getattr(comment.post, "author", None):
        return 0

    actor_name = get_user_display_name(actor) if actor else (comment.author_name or gettext("Someone"))
    post_title = comment.post.safe_translation_getter("title", any_language=True) or ""
    notification, created = create_notification(
        recipient=recipient,
        actor=actor,
        notification_type=UserNotification.NotificationType.REPLY_TO_YOUR_COMMENT,
        title=gettext("New reply to your comment"),
        message=gettext('%(user)s replied to your comment on "%(title)s".')
        % {"user": actor_name, "title": post_title},
        url=f"{comment.post.get_absolute_url()}#comment-{comment.id}",
        related_post=comment.post,
        payload={
            "comment_id": comment.id,
            "parent_comment_id": parent.id,
            "post_id": comment.post_id,
            "post_title": post_title,
            "actor_name": actor_name,
        },
        dedupe_key=f"reply-to-comment:{comment.id}:{recipient.id}",
    )
    if created:
        send_notification_email(notification)
    return 1 if created else 0


def create_new_follower_notification(*, follower, followed):
    if not follower or not followed or follower == followed:
        return 0

    follower_name = get_user_display_name(follower)
    notification, created = create_notification(
        recipient=followed,
        actor=follower,
        notification_type=UserNotification.NotificationType.NEW_FOLLOWER,
        title=gettext("You have a new follower"),
        message=gettext("%(user)s started following you.") % {"user": follower_name},
        url=f"/es/accounts/profile/{follower.username}/",
        payload={"follower_id": follower.id, "follower_username": follower.username},
        dedupe_key=f"new-follower:{follower.id}:{followed.id}",
    )
    if created:
        send_notification_email(notification)
    return 1 if created else 0


def create_post_favorited_notification(*, post, actor):
    recipient = getattr(post, "author", None)
    if recipient is None or actor == recipient:
        return 0

    actor_name = get_user_display_name(actor)

    _, created = create_notification(
        recipient=recipient,
        actor=actor,
        notification_type=UserNotification.NotificationType.POST_FAVORITED,
        title=gettext("New favorite on your post"),
        message=gettext('%(user)s added your post "%(title)s" to favorites.')
        % {
            "user": actor_name,
            "title": post.safe_translation_getter("title", any_language=True) or "",
        },
        url=post.get_absolute_url(),
        related_post=post,
        payload={
            "post_id": post.id,
            "post_title": post.safe_translation_getter("title", any_language=True) or "",
            "actor_name": actor_name,
        },
        dedupe_key=f"post-favorited:{post.id}:{actor.id}:{recipient.id}",
    )
    return 1 if created else 0


def get_unread_notifications_count(user):
    if not getattr(user, "is_authenticated", False):
        return 0
    return user.notifications.filter(is_read=False).count()
