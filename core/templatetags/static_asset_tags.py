"""Template helpers for cache-safe public static assets."""

from pathlib import Path

from django import template
from django.conf import settings


register = template.Library()


@register.simple_tag
def static_asset_version(asset_path):
    """Return a deployment-specific version for a local static asset.

    The web server deliberately caches public static files for several days.
    A version derived from the collected file means a new deployment is fetched
    immediately, while normal page loads keep using the browser cache.
    """
    relative_path = Path(str(asset_path).lstrip("/"))
    roots = [getattr(settings, "STATIC_ROOT", None), *getattr(settings, "STATICFILES_DIRS", [])]

    for root in roots:
        if not root:
            continue
        candidate = Path(root) / relative_path
        try:
            stat = candidate.stat()
        except OSError:
            continue
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"

    # The asset URL remains valid even if collectstatic has not run yet.
    return "1"
