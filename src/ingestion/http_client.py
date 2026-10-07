"""Cliente HTTP centralizado con headers realistas y tolerancia a fallos."""

import logging
from typing import Dict, Optional
import requests

logger = logging.getLogger("dnr.http_client")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 DNR-Bot/1.0"
)

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}


def fetch_url_content(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
) -> Optional[str]:
    """Obtiene el contenido de una URL manejando errores y timeouts.

    Retorna el texto obtenido o None si ocurrió un error.
    """
    request_headers = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        response = requests.get(url, headers=request_headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.warning("Fallo al obtener URL %s: %s", url, e)
        return None
