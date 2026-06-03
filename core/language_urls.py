import logging
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.utils import translation
from django.utils.translation import override
from django.utils.translation import gettext_lazy as _
from parler.utils.context import switch_language


logger = logging.getLogger(__name__)


def replace_language_prefix(full_path, target_language):
    if not full_path:
        return f"/{target_language}/"

    split = urlsplit(full_path)
    path = split.path or "/"
    language_codes = [code for code, _label in settings.LANGUAGES]
    parts = path.strip("/").split("/")

    if parts and parts[0] in language_codes:
        parts[0] = target_language
        new_path = "/" + "/".join(parts)
        if path.endswith("/") and not new_path.endswith("/"):
            new_path += "/"
    else:
        if path == "/":
            new_path = f"/{target_language}/"
        else:
            new_path = f"/{target_language}{path}"

    return urlunsplit(
        (
            split.scheme,
            split.netloc,
            new_path,
            split.query,
            split.fragment,
        )
    )


def get_best_language_url(
    current_path,
    target_language,
    *,
    translatable_object=None,
    language_urls=None,
):
    if not target_language:
        return current_path or "/"

    explicit_url = (language_urls or {}).get(target_language)
    if explicit_url:
        return explicit_url

    if translatable_object:
        try:
            get_absolute_url_for_language = getattr(
                translatable_object,
                "get_absolute_url_for_language",
                None,
            )
            if callable(get_absolute_url_for_language):
                url = get_absolute_url_for_language(target_language)
                if url:
                    return url
        except Exception:
            logger.warning(
                _("Failed to resolve the translated URL via the direct language URL helper."),
                exc_info=True,
            )

        try:
            has_translation = getattr(translatable_object, "has_translation", None)
            if callable(has_translation) and translatable_object.has_translation(target_language):
                with override(target_language):
                    with switch_language(translatable_object, target_language):
                        return translatable_object.get_absolute_url()
        except Exception:
            logger.warning(
                _("Failed to resolve the translated URL from the available object translation."),
                exc_info=True,
            )

        current_language = translation.get_language()
        try:
            with translation.override(target_language):
                url = translatable_object.get_absolute_url()
                if url:
                    return url
        except Exception:
            logger.warning(
                _("Failed to resolve the translated URL under the language override."),
                exc_info=True,
            )
        finally:
            translation.activate(current_language)

    return replace_language_prefix(current_path, target_language)
