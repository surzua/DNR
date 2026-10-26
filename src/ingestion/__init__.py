"""Ingestion modules for news RSS, Reddit, and search trends."""

import logging
import re
from typing import List, Optional, Set
from src.ingestion.models import NewsArticle
from src.ingestion.news_rss import fetch_rss_feeds, normalize_link
from src.ingestion.reddit_client import fetch_reddit_threads
from src.ingestion.scheduled_events import fetch_scheduled_events
from src.ingestion.trends_client import fetch_trending_topics

logger = logging.getLogger("dnr.ingestion")

__all__ = [
    "NewsArticle",
    "fetch_rss_feeds",
    "fetch_reddit_threads",
    "fetch_trending_topics",
    "fetch_scheduled_events",
    "gather_all_sources",
]


def _event_tokens(title: str) -> Set[str]:
    return {word for word in re.findall(r"[a-záéíóúñü0-9]{3,}", title.lower())}


def group_articles_by_event(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Anota cobertura similar sin confundir repetición con corroboración.

    La agrupación es deliberadamente conservadora: solo une titulares con una
    similitud léxica alta y mantiene cada artículo original para su trazabilidad.
    """
    groups: List[List[NewsArticle]] = []
    for article in articles:
        tokens = _event_tokens(article.title)
        matching_group = None
        for group in groups:
            reference = _event_tokens(group[0].title)
            union = tokens | reference
            if union and len(tokens & reference) / len(union) >= 0.6:
                matching_group = group
                break
        (matching_group if matching_group is not None else groups.append([]) or groups[-1]).append(article)

    for index, group in enumerate(groups, start=1):
        if len(group) < 2:
            continue
        sources = sorted({article.source for article in group})
        for article in group:
            article.event_key = f"event-{index:03d}"
            article.corroborating_sources = [source for source in sources if source != article.source]
    return articles


def gather_all_sources(
    config_path: str = "config/sources.yaml",
    lookback_hours: Optional[int] = None,
) -> List[NewsArticle]:
    """Orquestador central de la capa de ingesta.

    Obtiene artículos de medios de prensa chilenos (RSS), discusiones ciudadanas,
    eventos previsibles y señales opcionales de búsquedas,
    aplica deduplicación transversal y retorna una lista unificada de NewsArticle.
    """
    logger.info("Iniciando recolección integral de fuentes (Prensa RSS + Reddit)...")

    # 1. Ingesta de prensa RSS
    rss_articles = fetch_rss_feeds(config_path=config_path, lookback_hours=lookback_hours)

    # 2. Ingesta de Reddit
    reddit_articles = fetch_reddit_threads(config_path=config_path, lookback_hours=lookback_hours)

    # 3. Señales opcionales: sus fallos no bloquean la ingesta principal.
    trend_articles = fetch_trending_topics(config_path=config_path)
    scheduled_articles = fetch_scheduled_events(config_path=config_path)

    # 4. Consolidación y deduplicación transversal
    combined: List[NewsArticle] = []
    seen_links: Set[str] = set()
    seen_titles: Set[str] = set()

    for item in rss_articles + reddit_articles + trend_articles + scheduled_articles:
        norm_link = normalize_link(item.link)
        norm_title = item.title.lower()

        if norm_link in seen_links or norm_title in seen_titles:
            continue

        seen_links.add(norm_link)
        seen_titles.add(norm_title)
        combined.append(item)

    group_articles_by_event(combined)
    logger.info(
        "Recolección completa finalizada: %d señales (%d RSS + %d Reddit + %d Trends + %d eventos)",
        len(combined),
        len(rss_articles),
        len(reddit_articles),
        len(trend_articles),
        len(scheduled_articles),
    )
    return combined
