from django import template
from bs4 import BeautifulSoup
from django.utils.timesince import timesince
from django.utils.translation import get_language

register = template.Library()

@register.filter
def add_zoom_class_to_images(html):
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        existing_class = img.get("class", [])
        if "zoomable" not in existing_class:
            existing_class.append("zoomable")
            img['class'] = existing_class
    return str(soup)


@register.filter
def replace_year(value, year):
    if not value:
        return ""
    return str(value).replace("{year}", str(year))


@register.filter
def relative_time(value):
    """Render a natural relative time with language-appropriate word order."""
    if not value:
        return ""

    duration = timesince(value)
    language = (get_language() or "en").split("-")[0]
    if language == "es":
        return f"Hace {duration.replace(', ', ' y ')}"
    if language == "ca":
        return f"Fa {duration.replace(', ', ' i ')}"
    return f"{duration} ago"
