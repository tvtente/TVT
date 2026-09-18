"""Minimal, signed cookie-consent handling without visitor profiling."""

from datetime import datetime, timezone

from django.conf import settings
from django.core import signing


COOKIE_NAME = "tvt_cookie_consent"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60
COOKIE_VERSION = 1
OPTIONAL_CATEGORIES = ("analytics", "marketing")


def default_consent():
    return {
        "has_choice": False,
        "preferences": True,
        "analytics": False,
        "marketing": False,
        "timestamp": None,
    }


def read_consent(request):
    raw_value = request.COOKIES.get(COOKIE_NAME)
    if not raw_value:
        return default_consent()
    try:
        value = signing.loads(raw_value, salt="tvt.cookie-consent", max_age=COOKIE_MAX_AGE)
    except signing.BadSignature:
        return default_consent()
    if not isinstance(value, dict) or value.get("version") != COOKIE_VERSION:
        return default_consent()
    consent = default_consent()
    consent.update(
        has_choice=True,
        analytics=bool(value.get("analytics")),
        marketing=bool(value.get("marketing")),
        timestamp=value.get("timestamp"),
    )
    return consent


def consent_value(*, analytics=False, marketing=False):
    return signing.dumps(
        {
            "version": COOKIE_VERSION,
            "analytics": bool(analytics),
            "marketing": bool(marketing),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        salt="tvt.cookie-consent",
    )


def set_consent_cookie(response, *, analytics=False, marketing=False):
    response.set_cookie(
        COOKIE_NAME,
        consent_value(analytics=analytics, marketing=marketing),
        max_age=COOKIE_MAX_AGE,
        secure=bool(getattr(settings, "SESSION_COOKIE_SECURE", False)),
        httponly=True,
        samesite="Lax",
    )
    return response
