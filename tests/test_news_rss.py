"""Unit tests for the RSS news ingestion module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest

from src.ingestion.news_rss import fetch_rss_feeds, normalize_link, parse_feed_entry

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Medio de Prueba</title>
    <link>https://ejemplo.cl</link>
    <description>Noticias de prueba</description>
    <item>
      <title>Noticia Reciente 1</title>
      <link>https://ejemplo.cl/noticia-1?utm_source=rss</link>
      <description>&lt;p&gt;Resumen con &lt;b&gt;HTML&lt;/b&gt; y texto.&lt;/p&gt;</description>
      <pubDate>{recent_date}</pubDate>
    </item>
    <item>
      <title>Noticia Antigua</title>
      <link>https://ejemplo.cl/noticia-antigua</link>
      <description>Noticia de hace 5 días</description>
      <pubDate>{old_date}</pubDate>
    </item>
    <item>
      <title>Noticia Duplicada</title>
      <link>https://ejemplo.cl/noticia-1</link>
      <description>Mismo link normalizado</description>
      <pubDate>{recent_date}</pubDate>
    </item>
  </channel>
</rss>
"""


def test_normalize_link():
    url_with_params = "https://www.latercera.com/nacional/noticia/?utm_source=rss&utm_medium=feed"
    normalized = normalize_link(url_with_params)
    assert normalized == "https://www.latercera.com/nacional/noticia"

    url_trailing_slash = "https://www.df.cl/economia/mercados/"
    assert normalize_link(url_trailing_slash) == "https://www.df.cl/economia/mercados"


def test_parse_feed_entry_filtering_and_cleaning():
    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=2)
    cutoff = now - timedelta(hours=24)

    # Entrada reciente y válida
    entry_valid = {
        "title": "  Reforma tributaria avanza en el Congreso  ",
        "link": "https://df.cl/reforma",
        "summary": "<p>El proyecto &amp; acuerdo avanza.</p>",
        "published_parsed": recent.timetuple(),
    }
    article = parse_feed_entry(entry_valid, source_name="DF", category="economia", cutoff_time=cutoff)
    assert article is not None
    assert article.title == "Reforma tributaria avanza en el Congreso"
    assert article.summary == "El proyecto & acuerdo avanza."
    assert article.source == "DF"
    assert article.category == "economia"

    # Entrada antigua (fuera de cutoff)
    old = now - timedelta(hours=48)
    entry_old = {
        "title": "Noticia vieja",
        "link": "https://df.cl/vieja",
        "published_parsed": old.timetuple(),
    }
    assert parse_feed_entry(entry_old, source_name="DF", cutoff_time=cutoff) is None

    # Entrada sin enlace ni título
    assert parse_feed_entry({"title": ""}, source_name="DF") is None
    assert parse_feed_entry({"title": "Test", "link": ""}, source_name="DF") is None


def test_fetch_rss_feeds_mocked(tmp_path):
    now = datetime.now(timezone.utc)
    recent_str = (now - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    old_str = (now - timedelta(days=5)).strftime("%a, %d %b %Y %H:%M:%S +0000")

    xml_content = SAMPLE_RSS_XML.format(recent_date=recent_str, old_date=old_str)

    config_content = """
rss_feeds:
  medio_test:
    name: "Medio Test"
    categories:
      nacional: "https://ejemplo.cl/rss"
pipeline:
  max_hours_lookback: 24
"""
    cfg_file = tmp_path / "sources_test.yaml"
    cfg_file.write_text(config_content, encoding="utf-8")

    with patch("src.ingestion.news_rss.fetch_url_content", return_value=xml_content):
        articles = fetch_rss_feeds(config_path=str(cfg_file), lookback_hours=24)

    # Debería haber exactamente 1 artículo:
    # - "Noticia Reciente 1" entra
    # - "Noticia Antigua" se descarta por fecha (>24h)
    # - "Noticia Duplicada" se descarta por URL duplicada (https://ejemplo.cl/noticia-1)
    assert len(articles) == 1
    assert articles[0].title == "Noticia Reciente 1"
    assert articles[0].source == "Medio Test"
