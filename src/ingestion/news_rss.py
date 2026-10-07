"""Parser de feeds RSS de prensa chilena con resiliencia, sanitización y deduplicación."""

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, urlunparse
import feedparser
import yaml

from src.ingestion.http_client import fetch_url_content
from src.ingestion.models import NewsArticle

logger = logging.getLogger("dnr.news_rss")


def normalize_link(link: str) -> str:
    """Normaliza una URL eliminando parámetros de consulta y fragmentos para deduplicar."""
    if not link:
        return ""
    parsed = urlparse(link.strip())
    # Preservamos solo esquema, netloc y path
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", "")).lower()


def parse_feed_entry(
    entry: Any,
    source_name: str,
    category: Optional[str] = None,
    cutoff_time: Optional[datetime] = None,
) -> Optional[NewsArticle]:
    """Parsea una entrada de feedparser a un NewsArticle validado.

    Descarta artículos fuera de la ventana temporal o con datos mínimos faltantes.
    """
    title = entry.get("title", "").strip()
    if not title:
        return None

    # Extracción de enlace
    link = entry.get("link", "").strip()
    if not link and entry.get("links"):
        for l in entry.get("links", []):
            if isinstance(l, dict) and l.get("href"):
                link = l["href"].strip()
                break

    if not link:
        return None

    # Extracción de resumen
    summary = entry.get("summary", entry.get("description", ""))

    # Extracción de fecha
    pub_dt: Optional[datetime] = None
    parsed_time = entry.get("published_parsed")
    if parsed_time:
        try:
            pub_dt = datetime(*parsed_time[:6], tzinfo=timezone.utc)
        except Exception:
            pub_dt = None

    if pub_dt is None and entry.get("published"):
        try:
            from dateutil import parser
            parsed = parser.parse(entry.published)
            pub_dt = parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pub_dt = None

    if pub_dt is None:
        # Fallback a fecha actual en UTC si el feed no entrega fecha
        pub_dt = datetime.now(timezone.utc)

    # Filtrar por ventana temporal si se especificó cutoff
    if cutoff_time and pub_dt < cutoff_time:
        return None

    return NewsArticle(
        title=title,
        link=link,
        summary=summary,
        published_at=pub_dt,
        source=source_name,
        category=category,
    )


def fetch_rss_feeds(
    config_path: str = "config/sources.yaml",
    lookback_hours: Optional[int] = None,
) -> List[NewsArticle]:
    """Obtiene y parsea artículos desde todos los feeds RSS configurados.

    Aplica deduplicación intra e inter-feed, filtrado por fecha y degradación suave ante errores.
    """
    path = Path(config_path)
    if not path.exists():
        logger.error("Archivo de configuración %s no encontrado", config_path)
        return []

    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f) or {}

    rss_config = config.get("rss_feeds", {})
    if not rss_config:
        logger.warning("No se encontraron rss_feeds configurados en %s", config_path)
        return []

    pipeline_cfg = config.get("pipeline", {})
    hours = lookback_hours if lookback_hours is not None else pipeline_cfg.get("max_hours_lookback", 24)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    articles: List[NewsArticle] = []
    seen_links: Set[str] = set()
    seen_titles: Set[str] = set()

    total_feeds = 0
    successful_feeds = 0

    for source_key, source_data in rss_config.items():
        source_name = source_data.get("name", source_key)
        categories = source_data.get("categories", {})

        for cat_name, feed_url in categories.items():
            total_feeds += 1
            logger.info("Obteniendo feed: %s [%s] -> %s", source_name, cat_name, feed_url)

            content = fetch_url_content(feed_url)
            if not content:
                logger.warning("Omitiendo feed inaccesible: %s (%s)", source_name, feed_url)
                continue

            try:
                parsed_feed = feedparser.parse(content)
            except Exception as exc:
                logger.warning("Error parseando XML del feed %s (%s): %s", source_name, feed_url, exc)
                continue

            successful_feeds += 1
            feed_articles = 0

            for entry in parsed_feed.entries:
                article = parse_feed_entry(
                    entry=entry,
                    source_name=source_name,
                    category=cat_name,
                    cutoff_time=cutoff_time,
                )
                if not article:
                    continue

                norm_link = normalize_link(article.link)
                norm_title = article.title.lower()

                # Deduplicación por enlace o título idéntico
                if norm_link in seen_links or norm_title in seen_titles:
                    continue

                seen_links.add(norm_link)
                seen_titles.add(norm_title)
                articles.append(article)
                feed_articles += 1

            logger.info(
                "Feed procesado: %s [%s] -> %d artículos válidos (últimas %dh)",
                source_name,
                cat_name,
                feed_articles,
                hours,
            )

    logger.info(
        "Ingesta RSS completada: %d artículos recolectados de %d/%d feeds exitosos",
        len(articles),
        successful_feeds,
        total_feeds,
    )
    return articles
