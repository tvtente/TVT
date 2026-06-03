from django import template
from bs4 import BeautifulSoup

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
