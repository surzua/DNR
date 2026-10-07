"""Ingestion modules for news RSS, Reddit, and search trends."""

import logging
from typing import List, Optional, Set
from src.ingestion.models import NewsArticle
from src.ingestion.news_rss import fetch_rss_feeds, normalize_link
from src.ingestion.reddit_client import fetch_reddit_threads

logger = logging.getLogger("dnr.ingestion")

__all__ = [
    "NewsArticle",
    "fetch_rss_feeds",
    "fetch_reddit_threads",
    "gather_all_sources",
]


def gather_all_sources(
    config_path: str = "config/sources.yaml",
    lookback_hours: Optional[int] = None,
) -> List[NewsArticle]:
    """Orquestador central de la capa de ingesta.

    Obtiene artículos de medios de prensa chilenos (RSS) y discusiones ciudadanas (Reddit),
    aplica deduplicación transversal y retorna una lista unificada de NewsArticle.
    """
    logger.info("Iniciando recolección integral de fuentes (Prensa RSS + Reddit)...")

    # 1. Ingesta de prensa RSS
    rss_articles = fetch_rss_feeds(config_path=config_path, lookback_hours=lookback_hours)

    # 2. Ingesta de Reddit
    reddit_articles = fetch_reddit_threads(config_path=config_path, lookback_hours=lookback_hours)

    # 3. Consolidación y deduplicación transversal
    combined: List[NewsArticle] = []
    seen_links: Set[str] = set()
    seen_titles: Set[str] = set()

    for item in rss_articles + reddit_articles:
        norm_link = normalize_link(item.link)
        norm_title = item.title.lower()

        if norm_link in seen_links or norm_title in seen_titles:
            continue

        seen_links.add(norm_link)
        seen_titles.add(norm_title)
        combined.append(item)

    logger.info(
        "Recolección completa finalizada: %d artículos combinados (%d RSS + %d Reddit)",
        len(combined),
        len(rss_articles),
        len(reddit_articles),
    )
    return combined
