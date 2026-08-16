"""Generación de borradores con un modelo local servido por Ollama."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


class ReplyGenerationError(Exception):
    """Error seguro para mostrar al operador del panel."""


@dataclass(frozen=True)
class GeneratedReply:
    text: str
    model_name: str
    risk_level: str


def generate_reply(*, comment, fan) -> GeneratedReply:
    """Crea un borrador; jamás envía nada a Instagram."""
    if settings.USE_LLAMA:
        return _generate_with_llama(comment=comment, fan=fan)
    raise ReplyGenerationError(
        "Llama local está desactivado. Configura USAR_LLAMA_SINO_OPENAI=yes en .env."
    )


def _generate_with_llama(*, comment, fan) -> GeneratedReply:
    prompt = _build_prompt(comment=comment, fan=fan)
    payload = json.dumps(
        {
            "model": settings.LLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4},
        }
    ).encode("utf-8")
    request = Request(
        f"{settings.LLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ReplyGenerationError(f"Ollama respondió con error HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise ReplyGenerationError(
            "No se puede conectar con Ollama. Ejecuta 'ollama serve' y comprueba LLAMA_BASE_URL."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplyGenerationError("Ollama devolvió una respuesta que no se pudo interpretar.") from exc

    text = " ".join(str(data.get("response", "")).split())
    if not text:
        raise ReplyGenerationError("Ollama no generó texto. Comprueba el modelo configurado.")

    return GeneratedReply(
        text=text[:600],
        model_name=settings.LLAMA_MODEL,
        risk_level=_risk_level(comment.text),
    )


def _build_prompt(*, comment, fan) -> str:
    channel = "mensaje directo" if hasattr(comment, "recipient_platform_id") else "comentario público"
    return f"""CANAL: {channel}

FAN_PROFILE AUTORIZADO:
{_fan_profile_context(fan)}

MENSAJE RECIBIDO:
{comment.text}

Responde ahora como Tavata. Usa solo el perfil autorizado y el mensaje
recibido; no inventes recuerdos, datos ni contexto. Devuelve únicamente
la respuesta para esa persona."""


def _fan_profile_context(fan) -> str:
    """Prepara únicamente los datos de perfil autorizados para el modelo.

    Las notas internas del panel no se mandan: pueden contener información no
    verificada o sensible. La regla individual sí es una configuración expresa
    del equipo para personalizar el trato de ese fan concreto.
    """
    lines = [
        f"username: {fan.username or '(no disponible)'}",
        f"nombre autorizado: {fan.display_name or '(no disponible)'}",
        f"tipo de fan: {fan.get_profile_type_display()}",
    ]
    try:
        rule = fan.rule
    except ObjectDoesNotExist:
        rule = None

    if rule:
        if rule.preferred_names:
            lines.append(f"nombres o apodos autorizados: {_clean_context(rule.preferred_names)}")
        if rule.tone:
            lines.append(f"tono preferido: {_clean_context(rule.tone)}")
        if rule.emojis:
            lines.append(f"emojis autorizados: {_clean_context(rule.emojis)}")
        if rule.forbidden_topics:
            lines.append(f"temas que no debes abordar: {_clean_context(rule.forbidden_topics)}")
        if rule.special_context:
            lines.append(f"contexto especial autorizado: {_clean_context(rule.special_context)}")
        if rule.human_review_required:
            lines.append("esta respuesta requiere revisión humana antes de enviarse")
    return "\n".join(f"- {line}" for line in lines)


def _clean_context(value: str, limit: int = 700) -> str:
    """Evita que un campo del panel monopolice el contexto del modelo."""
    return " ".join(value.split())[:limit]


def _risk_level(text: str) -> str:
    """Clasificación local sencilla: la revisión humana sigue siendo obligatoria."""
    normalized = text.lower()
    high_risk_terms = ("médic", "medic", "abogado", "legal", "denuncia", "emergencia", "suicid", "tarjeta", "cuenta bancaria")
    medium_risk_terms = ("precio", "pago", "teléfono", "telefono", "dirección", "direccion", "queja", "reclamo")
    if any(term in normalized for term in high_risk_terms):
        return "high"
    if any(term in normalized for term in medium_risk_terms):
        return "medium"
    return "low"
