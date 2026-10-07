"""Tests for data models in ingestion."""

from datetime import datetime, timezone
from src.ingestion.models import NewsArticle


def test_news_article_normalization():
    article = NewsArticle(
        title="  Noticia de prueba con   espacios   ",
        link="https://ejemplo.cl/noticia",
        summary="<p>Resumen   limpio</p>",
        published_at="2026-10-06T12:00:00-03:00",
        source="EMOL",
        category="Economía",
    )

    assert article.title == "Noticia de prueba con espacios"
    assert article.published_at.tzinfo is not None
    # 12:00 at UTC-3 is 15:00 UTC
    assert article.published_at == datetime(2026, 10, 6, 15, 0, 0, tzinfo=timezone.utc)
    assert article.source == "EMOL"
