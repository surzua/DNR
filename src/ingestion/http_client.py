"""Cliente HTTP centralizado con headers realistas y tolerancia a fallos."""

import logging
from urllib.parse import urlparse
from typing import Dict, Optional
import requests

logger = logging.getLogger("dnr.http_client")

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB límite máximo para evitar OOM / Stream DoS

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
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> Optional[str]:
    """Obtiene el contenido de una URL de forma segura y acotada en memoria.

    Valida esquemas web seguros (http/https), aplica stream acotado y maneja timeouts.
    Retorna el texto obtenido o None si ocurrió un error o la URL es insegura.
    """
    if not url or not isinstance(url, str):
        return None

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        logger.warning("Rechazada petición a URL con esquema no seguro o inválido: %s", url)
        return None

    request_headers = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        response = requests.get(
            url,
            headers=request_headers,
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()

        chunks = []
        total_downloaded = 0
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total_downloaded += len(chunk)
            if total_downloaded > max_bytes:
                logger.warning(
                    "Respuesta de %s excedió límite seguro (%d bytes). Interrumpiendo lectura...",
                    url,
                    max_bytes,
                )
                chunks.append(chunk[: max_bytes - (total_downloaded - len(chunk))])
                break
            chunks.append(chunk)

        encoding = response.encoding or "utf-8"
        raw_bytes = b"".join(chunks)
        return raw_bytes.decode(encoding, errors="replace")
    except requests.exceptions.RequestException as e:
        logger.warning("Fallo al obtener URL %s: %s", url, e)
        return None
