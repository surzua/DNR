"""Señales opcionales desde el RSS público de Google Trends."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List

import feedparser
import requests
import yaml

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
        if response.status_code != 200:
            logger.warning("Trends Chile no disponible: HTTP %s; se continúa sin esta señal.", response.status_code)
            return []
        feed = feedparser.parse(response.content)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Trends Chile no disponible: %s; se continúa sin esta señal.", exc)
        return []

    topics: List[NewsArticle] = []
    for entry in feed.entries[:limit]:
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        link = str(entry.get("link", TRENDS_RSS_URL)).strip() or TRENDS_RSS_URL
        topics.append(NewsArticle(
            title=title, link=link, summary=str(entry.get("summary", "")).strip(),
            published_at=now, first_detected_at=now, publication_date_is_estimated=True,
            source="Google Trends Chile (RSS público)", category="Señal de búsqueda",
            signal_type="search_trend",
            signal_limitations="RSS público observado en esta hora; no entrega cifras exactas ni confirma hechos.",
        ))
    logger.info("Trends Chile: %d señales públicas recuperadas.", len(topics))
    return topics
