"""Pruebas de procedencia, eventos y señales opcionales de descubrimiento."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.analysis.opportunity_eval import Opportunity, filter_and_rank_opportunities
from src.analysis.prompt_templates import format_article_snippet
from src.ingestion import group_articles_by_event
from src.ingestion.models import NewsArticle
from src.ingestion.trends_client import fetch_trending_topics


def _opportunity(**changes: str) -> Opportunity:
    values = {
        "headline": "Producto de prueba", "category": "Deportes", "why_is_trending": "Evento activo",
        "contrarian_or_curious_angle": "Resolver una duda", "suggested_deliverable": "App web",
        "data_sources": [], "virality_score": 8, "technical_feasibility_score": 8,
        "fast_execution_strategy": "Definir alcance", "trigger_article_title": "Partido decisivo",
        "trigger_article_url": "https://ejemplo.cl/partido",
    }
    values.update(changes)
    return Opportunity(**values)


def test_context_preserves_dates_provenance_and_longer_summary():
    article = NewsArticle(
        title="Evento", link="https://ejemplo.cl/evento", summary="x" * 300,
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        first_detected_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 3, tzinfo=timezone.utc), source="Fuente",
        publication_date_is_estimated=False,
    )
    snippet = format_article_snippet(article, 1)
    assert "Publicación/evento: 2026-10-01" in snippet
    assert "Primera detección DNR: 2026-10-02" in snippet
    assert "Actualización fuente: 2026-10-03" in snippet
    assert "x" * 300 in snippet


def test_event_grouping_marks_related_coverage_without_removing_articles():
    now = datetime.now(timezone.utc)
    first = NewsArticle(title="Chile anuncia calendario del torneo 2026", link="https://a.cl/1", published_at=now, source="Medio A")
    second = NewsArticle(title="Calendario del torneo 2026 anunciado por Chile", link="https://b.cl/1", published_at=now, source="Medio B")
    grouped = group_articles_by_event([first, second])
    assert len(grouped) == 2
    assert grouped[0].event_key == grouped[1].event_key
    assert grouped[0].corroborating_sources == ["Medio B"]


def test_same_event_allows_distinct_products_but_not_same_need():
    calculator = _opportunity(product_type="Calculadora", user_need="Calcular costo", user_action="Ingresar consumo")
    game = _opportunity(headline="Desafío", product_type="Juego o desafío", user_need="Competir con amistades", user_action="Elegir escenario")
    duplicate = _opportunity(headline="Otra calculadora", product_type="Calculadora", user_need="Calcular costo", user_action="Ingresar consumo")
    accepted = filter_and_rank_opportunities([calculator, game, duplicate])
    assert {item.product_type for item in accepted} == {"Calculadora", "Juego o desafío"}


def test_trends_failure_degrades_without_stopping(tmp_path):
    config = tmp_path / "sources.yaml"
    config.write_text("trends:\n  enabled: true\n  limit: 3\n", encoding="utf-8")
    response = MagicMock(status_code=503)
    with patch("src.ingestion.trends_client.requests.get", return_value=response):
        assert fetch_trending_topics(str(config)) == []


def test_trends_keeps_interval_date_and_editorial_limit(tmp_path):
    config = tmp_path / "sources.yaml"
    config.write_text("trends:\n  enabled: true\n  limit: 3\n", encoding="utf-8")
    xml = b'''<?xml version="1.0"?><rss xmlns:ht="https://trends.google.com/trending/rss"><channel><item>
      <title>tema en Chile</title><link>https://trends.google.com/trending/rss?geo=CL</link>
      <pubDate>Mon, 26 Oct 2026 00:00:00 GMT</pubDate><ht:approx_traffic>100+</ht:approx_traffic>
      <ht:news_item_title>Noticia relacionada</ht:news_item_title>
      <ht:news_item_url>https://medio.cl/noticia</ht:news_item_url>
      <ht:news_item_source>Medio</ht:news_item_source>
    </item></channel></rss>'''
    response = MagicMock(status_code=200, headers={"content-type": "text/xml"}, content=xml)
    with patch("src.ingestion.trends_client.requests.get", return_value=response):
        topics = fetch_trending_topics(str(config))
    assert len(topics) == 1
    assert topics[0].search_traffic_label == "100+"
    assert topics[0].publication_date_is_estimated is False
    assert topics[0].link == "https://medio.cl/noticia"
    assert topics[0].related_news_urls == ["https://medio.cl/noticia"]
    assert topics[0].signal_source_url == "https://trends.google.com/trending/rss?geo=CL"
    assert "no confirma hechos" in (topics[0].signal_limitations or "")
