"""Comprobaciones HTTP acotadas para las fuentes propuestas por el radar.

La verificación confirma disponibilidad técnica de una fuente, no que sus datos
respondan correctamente a una hipótesis editorial. Por eso no descarga cuerpos
de respuesta ni sigue redirecciones: evita costes innecesarios y reduce la
superficie de SSRF frente a URLs producidas por un modelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import logging
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

import requests

from src.ingestion.http_client import DEFAULT_HEADERS

logger = logging.getLogger("dnr.source_verification")

_ACCEPTED_CONTENT_TYPES = (
    "text/",
    "json",
    "xml",
    "csv",
    "excel",
    "spreadsheet",
    "pdf",
    "octet-stream",
)


@dataclass(frozen=True)
class SourceCheck:
    """Resultado serializable de la comprobación técnica de una URL."""

    status: str
    checked_at: datetime
    url: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    error: str | None = None


def _safe_error(error: object) -> str:
    """Evita conservar trazas o respuestas remotas extensas en el historial."""
    return str(error).replace("\n", " ")[:200]


def validate_public_http_url(url: str) -> str | None:
    """Retorna un motivo de rechazo o ``None`` para una URL web admisible.

    Se rechazan hosts locales, IPs no globales, credenciales embebidas y puertos
    no estándar. La llamada no resuelve DNS; además, las redirecciones están
    desactivadas en la consulta posterior.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "URL sin esquema HTTP(S) o host válido"
    if parsed.username or parsed.password:
        return "URL con credenciales embebidas"
    try:
        port = parsed.port
    except ValueError:
        return "URL con puerto inválido"
    if port not in {None, 80, 443}:
        return "URL con puerto no estándar"

    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return "host local no permitido"
    try:
        if not ipaddress.ip_address(hostname).is_global:
            return "dirección IP no pública"
    except ValueError:
        pass
    return None


def verify_source_url(
    url: str,
    *,
    timeout_seconds: int = 10,
    request_get: Callable[..., Any] = requests.get,
) -> SourceCheck:
    """Comprueba que una URL de datos sea pública, accesible y de tipo legible."""
    checked_at = datetime.now(timezone.utc)
    invalid_reason = validate_public_http_url(url)
    if invalid_reason:
        return SourceCheck("failed", checked_at, url=url, error=invalid_reason)

    try:
        response = request_get(
            url,
            headers={**DEFAULT_HEADERS, "Range": "bytes=0-4095"},
            timeout=timeout_seconds,
            allow_redirects=False,
            stream=True,
        )
        http_status = int(response.status_code)
        headers = getattr(response, "headers", {}) or {}
        content_type = str(headers.get("content-type", "")).split(";", 1)[0].strip().lower()
        final_url = getattr(response, "url", None)
        final_url = final_url if isinstance(final_url, str) else url
        try:
            if not 200 <= http_status < 300:
                return SourceCheck(
                    "failed", checked_at, final_url, http_status, content_type or None,
                    f"respuesta HTTP {http_status}",
                )
            if not content_type or not any(token in content_type for token in _ACCEPTED_CONTENT_TYPES):
                return SourceCheck(
                    "failed", checked_at, final_url, http_status, content_type or None,
                    "tipo de contenido no verificable",
                )
            return SourceCheck("accessible", checked_at, final_url, http_status, content_type)
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except requests.exceptions.RequestException as exc:
        return SourceCheck("failed", checked_at, url=url, error=_safe_error(exc))


def _apply_check(source: Any, check: SourceCheck) -> None:
    """Copia el resultado a un DataSource Pydantic o a un objeto compatible."""
    source.verification_status = check.status
    source.verification_checked_at = check.checked_at
    source.verification_url = check.url
    source.verification_http_status = check.http_status
    source.verification_content_type = check.content_type
    source.verification_error = check.error


def verify_opportunity_sources(
    opportunity: Any,
    *,
    timeout_seconds: int = 10,
    request_get: Callable[..., Any] = requests.get,
    cache: dict[str, SourceCheck] | None = None,
) -> bool:
    """Comprueba URLs y retorna si alguna quedó técnicamente accesible.

    Las consultas textuales se conservan para el analista, pero no se presentan
    como evidencia editorial verificada. ``cache`` permite no consultar dos veces
    la misma URL durante una ejecución.
    """
    checks = cache if cache is not None else {}
    accessible = False
    for source in getattr(opportunity, "data_sources", []):
        reference = getattr(source, "potential_url_or_query", "").strip()
        parsed = urlparse(reference)
        if not parsed.scheme:
            _apply_check(
                source,
                SourceCheck(
                    "not_checkable",
                    datetime.now(timezone.utc),
                    error="la fuente es una consulta, no una URL directa",
                ),
            )
            continue

        check = checks.get(reference)
        if check is None:
            check = verify_source_url(
                reference,
                timeout_seconds=timeout_seconds,
                request_get=request_get,
            )
            checks[reference] = check
        _apply_check(source, check)
        accessible = accessible or check.status == "accessible"
    return accessible


def verify_opportunities_sources(
    opportunities: Iterable[Any], *, timeout_seconds: int = 10
) -> dict[int, bool]:
    """Verifica un lote reutilizando resultados de URLs repetidas."""
    cache: dict[str, SourceCheck] = {}
    return {
        id(opportunity): verify_opportunity_sources(
            opportunity, timeout_seconds=timeout_seconds, cache=cache
        )
        for opportunity in opportunities
    }
