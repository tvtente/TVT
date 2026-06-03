from bs4 import BeautifulSoup
import bleach
import markdown


MARKDOWN_EXTENSIONS = [
    "extra",
    "fenced_code",
    "tables",
    "sane_lists",
    "nl2br",
]

ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p",
    "pre",
    "code",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "br",
    "div",
    "span",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "blockquote",
    "img",
]

ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "code": ["class"],
    "pre": ["class"],
    "div": ["class"],
    "span": ["class"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = list(bleach.sanitizer.ALLOWED_PROTOCOLS) + ["data"]


def render_markdown_to_html(markdown_source):
    raw_html = markdown.markdown(markdown_source or "", extensions=MARKDOWN_EXTENSIONS)
    cleaned_html = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned_html = bleach.linkify(cleaned_html)
    soup = BeautifulSoup(cleaned_html, "html.parser")

    for image in soup.find_all("img"):
        classes = set(image.get("class", []))
        classes.add("zoomable")
        image["class"] = sorted(classes)
        if not image.has_attr("loading"):
            image["loading"] = "lazy"

    return str(soup)
