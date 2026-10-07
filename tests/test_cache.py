"""Unit tests for the articles cache module."""

from datetime import datetime, timezone
from src.ingestion.models import NewsArticle
from src.storage.articles_cache import load_articles_cache, save_articles_cache


def test_save_and_load_articles_cache(tmp_path):
    cache_file = tmp_path / "test_articles.json"
    now = datetime(2026, 10, 6, 18, 30, tzinfo=timezone.utc)

    sample_articles = [
        NewsArticle(
            title="Noticia Test 1",
            link="https://ejemplo.cl/1",
            summary="Resumen 1",
            published_at=now,
            source="La Tercera",
            category="Nacional",
        ),
        NewsArticle(
            title="Debate Test 2",
            link="https://reddit.com/r/chile/comments/2",
            summary="Resumen 2",
            published_at=now,
            source="Reddit (r/chile)",
            score=120,
            comments_count=45,
        ),
    ]

    saved_path = save_articles_cache(sample_articles, filepath=cache_file)
    assert saved_path.exists()

    loaded = load_articles_cache(filepath=cache_file)
    assert len(loaded) == 2
    assert loaded[0].title == "Noticia Test 1"
    assert loaded[0].source == "La Tercera"
    assert loaded[1].title == "Debate Test 2"
    assert loaded[1].score == 120
    assert loaded[1].comments_count == 45


def test_load_nonexistent_cache(tmp_path):
    nonexistent = tmp_path / "no_file.json"
    assert load_articles_cache(filepath=nonexistent) == []
