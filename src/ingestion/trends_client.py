"""Señales opcionales desde el RSS público de Google Trends."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List

import feedparser
import requests
import yaml
from dateutil import parser as date_parser

from src.ingestion.http_client import DEFAULT_HEADERS
from src.ingestion.models import NewsArticle

logger = logging.getLogger("dnr.trends_client")
TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=CL"


def fetch_trending_topics(config_path: str = "config/sources.yaml") -> List[NewsArticle]:
    """Lee tendencias públicas de Chile con degradación suave.

    El RSS no entrega un volumen exacto ni valida una afirmación. Si no está
    disponible, el radar continúa y el fallo queda explícito en los logs.
    """
    try:
        raw_config: Dict[str, Any] = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Trends omitido: no se pudo leer configuración (%s)", exc)
        return []
    trends_config = raw_config.get("trends", {})
    if not trends_config.get("enabled", False):
        return []

    now = datetime.now(timezone.utc)
    limit = int(trends_config.get("limit", 10))
    try:
        response = requests.get(TRENDS_RSS_URL, headers=DEFAULT_HEADERS, timeout=10)
        content_type = str(getattr(response, "headers", {}).get("content-type", "")).lower()
        if response.status_code != 200:
            logger.warning("Trends Chile no disponible: HTTP %s; se continúa sin esta señal.", response.status_code)
            return []
        if content_type and "xml" not in content_type and "rss" not in content_type:
            logger.warning("Trends Chile devolvió un tipo no XML (%s); se continúa sin esta señal.", content_type)
            return []
        feed = feedparser.parse(response.content)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Trends Chile no disponible: %s; se continúa sin esta señal.", exc)
        return []

    if getattr(feed, "bozo", False) and not feed.entries:
        logger.warning("Trends Chile devolvió XML inválido sin entradas; se continúa sin esta señal.")
        return []

    topics: List[NewsArticle] = []
    for entry in feed.entries[:limit]:
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        published_at = now
        estimated_date = True
        raw_published = entry.get("published") or entry.get("updated")
        if raw_published:
            try:
                parsed_date = date_parser.parse(str(raw_published))
                published_at = parsed_date.astimezone(timezone.utc) if parsed_date.tzinfo else parsed_date.replace(tzinfo=timezone.utc)
                estimated_date = False
            except (TypeError, ValueError, OverflowError):
                logger.warning("Trends Chile: fecha inválida para %r; se usará la hora de detección.", title)
        def _as_list(value: Any) -> List[str]:
            if isinstance(value, (list, tuple)):
                return [str(item).strip() for item in value if str(item).strip()]
            cleaned = str(value or "").strip()
            return [cleaned] if cleaned else []

        news_urls = _as_list(entry.get("ht_news_item_url"))
        news_sources = _as_list(entry.get("ht_news_item_source"))
        headlines = _as_list(entry.get("ht_news_item_title"))
        traffic_label = str(entry.get("ht_approx_traffic", "")).strip() or None
        summary = str(entry.get("summary", "")).strip()
        # El enlace del feed es común a todas las entradas y no sirve para
        # deduplicarlas; usar el artículo relacionado cuando existe y conservar
        # el RSS como procedencia separada.
        link = news_urls[0] if news_urls else (str(entry.get("link", TRENDS_RSS_URL)).strip() or TRENDS_RSS_URL)
        if headlines:
            summary = (summary + " " if summary else "") + "Noticias relacionadas: " + "; ".join(headlines[:3])
        topics.append(NewsArticle(
            title=title, link=link, summary=summary,
            published_at=published_at, first_detected_at=now, publication_date_is_estimated=estimated_date,
            source="Google Trends Chile (RSS público)", category="Señal de búsqueda",
            signal_type="search_trend",
            signal_limitations="Interés observado en el RSS; approx_traffic es un intervalo y no confirma hechos ni causalidad.",
            search_traffic_label=traffic_label, related_news_urls=news_urls, related_news_sources=news_sources,
            signal_source_url=TRENDS_RSS_URL,
        ))
    logger.info("Trends Chile: %d señales públicas recuperadas.", len(topics))
    return topics
