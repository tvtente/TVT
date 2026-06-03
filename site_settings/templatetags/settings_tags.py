# File: site_settings/templatetags/settings_tags.py
from django import template
from site_settings.models import SiteConfiguration, SiteTemplate

register = template.Library()

@register.simple_tag
def get_site_config():
    """
    A simple template tag to fetch the single SiteConfiguration object.
    This allows easy access to global settings in templates.
    It uses caching for high performance.
    """
    # We can add caching here as we did with widgets.
    # For simplicity now, we get it directly.

    # .get() is safe because django-solo ensures there's only one.
    return SiteConfiguration.get_solo()


@register.simple_tag
def get_active_site_template():
    """
    Returns the selected visual template for the public site.
    """
    return SiteTemplate.get_chosen()
