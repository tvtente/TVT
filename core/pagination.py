from django.core.paginator import Paginator

from site_settings.models import SiteConfiguration


def get_site_config_int(setting_name, default, *, logger=None, warning_message=None):
    try:
        site_config = SiteConfiguration.get_solo()
    except SiteConfiguration.DoesNotExist:
        if logger and warning_message:
            logger.warning(warning_message)
        return default

    return getattr(site_config, setting_name, default)


def paginate_queryset(queryset, page_number, per_page):
    return Paginator(queryset, per_page).get_page(page_number)
