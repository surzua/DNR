"""Unit tests for the unified ingestion aggregator."""

from datetime import datetime, timezone
from unittest.mock import patch
from src.ingestion import gather_all_sources
from src.ingestion.models import NewsArticle


def test_gather_all_sources_deduplication():
    now = datetime.now(timezone.utc)

    rss_mock = [
        NewsArticle(
            title="Escándalo de licitaciones públicas",
            link="https://latercera.com/politica/noticia1",
            published_at=now,
            source="La Tercera",
        ),
        NewsArticle(
            title="Inflación en Chile cae en septiembre",
            link="https://df.cl/economia/inflacion",
            published_at=now,
            source="DF",
        ),
    ]

    reddit_mock = [
        # Mismo titular que RSS (noticia compartida en Reddit)
        NewsArticle(
            title="Escándalo de licitaciones públicas",
            link="https://reddit.com/r/chile/comments/123",
            published_at=now,
            source="Reddit (r/chile)",
            score=150,
        ),
        # Noticia única de Reddit
        NewsArticle(
            title="¿Cómo ahorrar en dividendos este año?",
            link="https://reddit.com/r/chile/comments/456",
            published_at=now,
            source="Reddit (r/chile)",
            score=80,
        ),
    ]

    with patch("src.ingestion.fetch_rss_feeds", return_value=rss_mock), patch(
        "src.ingestion.fetch_reddit_threads", return_value=reddit_mock
    ):
        result = gather_all_sources()

    # Debería deduplicar el titular idéntico "Escándalo de licitaciones públicas"
    assert len(result) == 3
    titles = [a.title for a in result]
    assert "Escándalo de licitaciones públicas" in titles
    assert "Inflación en Chile cae en septiembre" in titles
    assert "¿Cómo ahorrar en dividendos este año?" in titles
