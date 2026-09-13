import logging

from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from accounts.models import get_user_avatar_url, get_user_default_avatar_url


register = template.Library()
logger = logging.getLogger(__name__)


@register.filter
def avatar_url(user):
    return get_user_avatar_url(user)


@register.filter
def default_avatar_url(user):
    """Static fallback selected in the user's profile preferences."""
    return get_user_default_avatar_url(user)


@register.filter
def safe_display_name(user):
    if not user:
        return ""
    try:
        profile = user.profile
        if profile:
            return profile.get_display_name()
    except ObjectDoesNotExist:
        pass
    except AttributeError:
        logger.warning(
            _("Failed to resolve the user display name from the profile."),
            exc_info=True,
        )
    return getattr(user, "get_full_name", lambda: "")() or getattr(user, "username", "")


@register.filter
def safe_bio(user):
    if not user:
        return ""
    try:
        profile = user.profile
        return (getattr(profile, "bio", "") or "").strip()
    except ObjectDoesNotExist:
        return ""
    except AttributeError:
        logger.warning(
            _("Failed to resolve the user biography from the profile."),
            exc_info=True,
        )
        return ""
