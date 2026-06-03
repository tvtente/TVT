"""
Infer gallery.Image.language from title, slug, and stored image path (no external APIs).

Used by guarded data migrations and tests; admin remains authoritative after migration.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

# Path / filename segments: _en, -english-, /es/, etc.
_PATH_LANG_REGEX = (
    (re.compile(r"(?:^|[/_-])(?:en|english|eng)(?:[._\-/]|$)", re.I), "en"),
    (re.compile(r"(?:^|[/_-])(?:es|esp|spanish)(?:[._\-/]|$)", re.I), "es"),
    (re.compile(r"(?:^|[/_-])(?:ca|catalan|català|catala)(?:[._\-/]|$)", re.I), "ca"),
)

# Exact stem segments (after splitting on - _ .) → language (weight applied separately).
_SEGMENT_LANG: dict[str, str] = {
    "justice": "en",
    "justicia": "es",
    "love": "en",
    "amor": "es",
    "news": "en",
    "noticias": "es",
    "welcome": "en",
    "bienvenido": "es",
    "bienvenida": "es",
    "benvinguda": "ca",
    "benvingut": "ca",
    "services": "en",
    "servicios": "es",
    "serveis": "ca",
    "contact": "en",
    "contacto": "es",
    "contacte": "ca",
    "company": "en",
    "empresa": "es",
    "article": "en",
    "articulo": "es",
    "english": "en",
    "espanol": "es",
    "español": "es",
    "catalan": "ca",
    "catala": "ca",
    "catalunya": "ca",
}

_ES_WORDS = frozenset(
    {
        "justicia",
        "amor",
        "español",
        "espanol",
        "años",
        "anos",
        "día",
        "dia",
        "más",
        "mas",
        "también",
        "tambien",
        "información",
        "informacion",
        "página",
        "pagina",
        "país",
        "pais",
        "noticia",
        "noticias",
        "servicios",
        "bienvenido",
        "bienvenida",
        "contenido",
        "artículo",
        "articulo",
        "resumen",
        "público",
        "publico",
        "española",
        "espanola",
    }
)
_EN_WORDS = frozenset(
    {
        "justice",
        "love",
        "english",
        "years",
        "information",
        "about",
        "welcome",
        "services",
        "company",
        "article",
        "summary",
        "content",
        "public",
        "blog",
        "news",
        "home",
        "video",
        "page",
        "read",
        "more",
    }
)
_CA_WORDS = frozenset(
    {
        "català",
        "catala",
        "catalunya",
        "informació",
        "informacio",
        "pàgina",
        "accés",
        "acces",
        "benvinguda",
        "benvingut",
        "serveis",
        "contacte",
        "generalitat",
        "barcelona",
        "lleida",
        "girona",
    }
)

_SEGMENT_WEIGHT = 3


def _haystack(title: str, slug: str, image_name: str, description: str) -> str:
    stem = PurePosixPath(image_name or "").stem
    parts = [
        (title or "").strip(),
        (slug or "").strip(),
        stem,
        (image_name or "").replace("\\", "/").lower(),
        (description or "").strip(),
    ]
    return " ".join(parts).lower()


def _segment_scores(stem: str) -> dict[str, int]:
    scores = {"es": 0, "en": 0, "ca": 0}
    if not stem:
        return scores
    for part in re.split(r"[-_.]+", stem.lower()):
        if len(part) < 3:
            continue
        lang = _SEGMENT_LANG.get(part)
        if lang:
            scores[lang] += _SEGMENT_WEIGHT
    return scores


def _keyword_scores(text: str) -> dict[str, int]:
    scores = {"es": 0, "en": 0, "ca": 0}
    for w in _ES_WORDS:
        if w in text:
            scores["es"] += 1
    for w in _EN_WORDS:
        if w in text:
            scores["en"] += 1
    for w in _CA_WORDS:
        if w in text:
            scores["ca"] += 1
    if "ñ" in text or "¿" in text or "¡" in text:
        scores["es"] += 2
    if "·" in text or "l·l" in text:
        scores["ca"] += 2
    return scores


def infer_gallery_image_language(
    *,
    title: str = "",
    slug: str = "",
    image_name: str = "",
    description: str = "",
) -> tuple[str, str]:
    """
    Return (language_code, reason_tag).

    language_code ∈ {es, en, ca}.
    reason_tag is for logging only: path_pattern, keyword, fallback_empty, fallback_tie.
    """
    text = _haystack(title, slug, image_name, description)
    stem = PurePosixPath(image_name or "").stem

    for rx, lang in _PATH_LANG_REGEX:
        if rx.search(text):
            return lang, "path_pattern"

    scores = {"es": 0, "en": 0, "ca": 0}
    for k, v in _segment_scores(stem).items():
        scores[k] += v
    for k, v in _keyword_scores(text).items():
        scores[k] += v

    best = max(scores.values())
    if best == 0:
        return "es", "fallback_empty"

    winners = [code for code, v in scores.items() if v == best]
    if len(winners) > 1:
        return "es", "fallback_tie"

    return winners[0], "keyword"
