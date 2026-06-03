from django.conf import settings
from books.cart import get_cart_count
from accounts.services import get_unread_notifications_count


def languages_context(request):
    return {
        'LANGUAGES': settings.LANGUAGES,
    }


def social_auth_context(request):
    return {
        'GOOGLE_AUTH_ENABLED': getattr(settings, 'GOOGLE_AUTH_ENABLED', False),
    }


def cart_context(request):
    return {
        "cart_count": get_cart_count(request),
    }


def notifications_context(request):
    return {
        "unread_notifications_count": get_unread_notifications_count(request.user),
    }
