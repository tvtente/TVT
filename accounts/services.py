from django.contrib.auth import get_user_model
from django.utils.translation import gettext

from accounts.models import UserFollow, UserNotification


User = get_user_model()


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

    _, created = create_notification(
        recipient=recipient,
        actor=actor,
        notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
        title=gettext("New comment on your post"),
        message=gettext('%(user)s commented on your post "%(title)s".')
        % {
            "user": actor_name,
            "title": post.safe_translation_getter("title", any_language=True) or "",
        },
        url=post.get_absolute_url(),
        related_post=post,
        payload={
            "comment_id": comment.id,
            "post_id": post.id,
            "post_title": post.safe_translation_getter("title", any_language=True) or "",
            "actor_name": actor_name,
        },
        dedupe_key=f"comment-on-post:{comment.id}:{recipient.id}",
    )
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
