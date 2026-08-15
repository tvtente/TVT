"""Generación de borradores con un modelo local servido por Ollama."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


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
    name = fan.display_name or fan.username or "la persona"
    return f"""Eres la asistente de Tavata y redactas un borrador breve para Instagram.
Responde en español, con calidez y respeto. No inventes información, no prometas resultados,
no pidas datos personales, no hables de pagos, ni des consejos médicos o legales.
Si el comentario necesita atención humana, invita con amabilidad a escribir por los canales oficiales.
Devuelve únicamente el texto de la respuesta, sin comillas ni explicaciones.

Persona: {name}
Comentario: {comment.text}
Respuesta:"""


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
