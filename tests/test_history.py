"""Tests for history management and deduplication."""

from datetime import datetime, timezone
from pathlib import Path
from src.storage.history_manager import (
    HistoryEntry,
    filter_articles_by_history,
    generate_next_id,
    get_entries_pending_delivery,
    get_recent_topics,
    get_recent_trigger_titles,
    get_recent_trigger_urls,
    load_history,
    normalize_title_for_dedup,
    normalize_url_for_dedup,
    save_history,
)


def test_history_save_and_load(tmp_path: Path):
    test_file = tmp_path / "history.json"

    entry1 = HistoryEntry(
        id="2026-10-06-001",
        timestamp=datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc),
        topic="Polémica por luminarias públicas",
        category="Política & Estado",
        viral_hook_type="Contrarian / Curious Hook",
        analytical_angle="Comparativa costo unitario vs presupuesto",
        data_sources=[{"name": "Mercado Público", "type": "API Pública"}],
        feasibility_score=8,
        virality_score=9,
        recommended_deliverable="Gráfico Estático de Alto Impacto",
        fast_execution_strategy="1. Scrape 2. Plot 3. Post",
        status="candidate",
    )

    save_history([entry1], filepath=test_file)
    loaded = load_history(filepath=test_file)

    assert len(loaded) == 1
    assert loaded[0].id == "2026-10-06-001"
    assert loaded[0].topic == "Polémica por luminarias públicas"
    assert loaded[0].evidence_status == "Propuesta (no verificada)"
    assert loaded[0].product_type is None


def test_delivery_state_is_backward_compatible_and_retryable():
    legacy_entry = HistoryEntry(
        id="2026-10-06-001",
        timestamp=datetime.now(timezone.utc),
        topic="Registro histórico",
        category="Deportes",
        viral_hook_type="Hook",
        analytical_angle="Angle",
        feasibility_score=7,
        virality_score=8,
        recommended_deliverable="App",
    )
    pending_entry = HistoryEntry.from_opportunity(
        type("OpportunityStub", (), {
            "headline": "Nueva alerta",
            "category": "Deportes",
            "contrarian_or_curious_angle": "Angle",
            "data_sources": [],
            "technical_feasibility_score": 7,
            "virality_score": 8,
            "suggested_deliverable": "App",
            "fast_execution_strategy": None,
            "trigger_article_title": None,
            "trigger_article_url": None,
        })(),
        entry_id="2026-10-06-002",
    )

    assert legacy_entry.delivery_status == "untracked"
    assert get_entries_pending_delivery([legacy_entry, pending_entry]) == [pending_entry]

    pending_entry.record_delivery_attempt(delivered=False)
    assert pending_entry.delivery_status == "failed"
    assert pending_entry.delivery_attempts == 1
    assert get_entries_pending_delivery([pending_entry]) == [pending_entry]

    pending_entry.record_delivery_attempt(delivered=True)
    assert pending_entry.delivery_status == "delivered"
    assert pending_entry.delivery_attempts == 2
    assert pending_entry.delivered_at is not None
    assert get_entries_pending_delivery([pending_entry]) == []


def test_generate_next_id():
    history = [
        HistoryEntry(
            id="2026-10-06-001",
            timestamp=datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc),
            topic="Tema 1",
            category="Deportes",
            viral_hook_type="Hook",
            analytical_angle="Angle",
            feasibility_score=7,
            virality_score=8,
            recommended_deliverable="App",
        ),
        HistoryEntry(
            id="2026-10-06-002",
            timestamp=datetime(2026, 10, 6, 11, 0, 0, tzinfo=timezone.utc),
            topic="Tema 2",
            category="Deportes",
            viral_hook_type="Hook",
            analytical_angle="Angle",
            feasibility_score=7,
            virality_score=8,
            recommended_deliverable="App",
        ),
    ]

    target_date = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    next_id = generate_next_id(history, target_date=target_date)
    assert next_id == "2026-10-06-003"


def test_get_recent_topics():
    history = [
        HistoryEntry(
            id="2026-10-06-001",
            timestamp=datetime(2026, 10, 6, 10, 0, 0, tzinfo=timezone.utc),
            topic="Tema Reciente",
            category="Deportes",
            viral_hook_type="Hook",
            analytical_angle="Angle",
            feasibility_score=7,
            virality_score=8,
            recommended_deliverable="App",
        ),
        HistoryEntry(
            id="2026-09-20-001",
            timestamp=datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc),
            topic="Tema Antiguo",
            category="Deportes",
            viral_hook_type="Hook",
            analytical_angle="Angle",
            feasibility_score=7,
            virality_score=8,
            recommended_deliverable="App",
        ),
    ]

    now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    recent = get_recent_topics(history=history, days=7, now=now)
    assert "Tema Reciente" in recent
    assert "Tema Antiguo" not in recent


def test_load_history_corrupt_file_preserves_backup(tmp_path: Path):
    corrupt_file = tmp_path / "history.json"
    corrupt_file.write_text("{ this is invalid json content ...", encoding="utf-8")

    loaded = load_history(filepath=corrupt_file)
    assert loaded == []

    backup_file = tmp_path / "history.corrupt.bak"
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == "{ this is invalid json content ..."


def test_normalize_url_and_title_for_dedup():
    url1 = "https://www.latercera.com/pulso/noticia/empleo-2026/?utm_source=rss&ref=home#comments"
    url2 = "http://latercera.com/pulso/noticia/empleo-2026"
    assert normalize_url_for_dedup(url1) == "latercera.com/pulso/noticia/empleo-2026"
    assert normalize_url_for_dedup(url1) == normalize_url_for_dedup(url2)
    assert normalize_url_for_dedup(None) == ""

    title1 = "¿Por qué los profesionales demoran 8 meses en encontrar empleo?"
    title2 = "Por que los profesionales demoran 8 meses en encontrar empleo"
    assert normalize_title_for_dedup(title1) == "por que los profesionales demoran 8 meses en encontrar empleo"
    assert normalize_title_for_dedup(title1) == normalize_title_for_dedup(title2)
    assert normalize_title_for_dedup(None) == ""


def test_get_recent_trigger_urls_and_titles():
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    entry_recent = HistoryEntry(
        id="2026-10-09-001",
        timestamp=datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc),
        topic="Proyecto A",
        category="Economía",
        viral_hook_type="Hook",
        analytical_angle="Angle",
        feasibility_score=8,
        virality_score=8,
        recommended_deliverable="Grafico",
        trigger_article_title="Noticia Reciente Sobre Finanzas",
        trigger_article_url="https://df.cl/mercados/dolar",
    )
    entry_old = HistoryEntry(
        id="2026-09-20-001",
        timestamp=datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc),
        topic="Proyecto B",
        category="Economía",
        viral_hook_type="Hook",
        analytical_angle="Angle",
        feasibility_score=8,
        virality_score=8,
        recommended_deliverable="Grafico",
        trigger_article_title="Noticia Antigua",
        trigger_article_url="https://df.cl/mercados/antigua",
    )

    history = [entry_recent, entry_old]
    urls = get_recent_trigger_urls(history=history, days=3, now=now)
    titles = get_recent_trigger_titles(history=history, days=3, now=now)

    assert "df.cl/mercados/dolar" in urls
    assert "df.cl/mercados/antigua" not in urls
    assert "Noticia Reciente Sobre Finanzas" in titles
    assert "Noticia Antigua" not in titles


def test_filter_articles_by_history():
    now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    history = [
        HistoryEntry(
            id="2026-10-09-001",
            timestamp=datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc),
            topic="Proyecto A",
            category="Economía",
            viral_hook_type="Hook",
            analytical_angle="Angle",
            feasibility_score=8,
            virality_score=8,
            recommended_deliverable="Grafico",
            trigger_article_title="Personas con estudios universitarios demoran más en encontrar empleo",
            trigger_article_url="https://www.latercera.com/pulso/noticia/desempleo-profesionales/",
        )
    ]

    art_repeated_url = {
        "title": "Titular ligeramente diferente de otra fuente",
        "link": "http://latercera.com/pulso/noticia/desempleo-profesionales/?ref=twitter",
    }
    art_repeated_title = {
        "title": "Personas con estudios universitarios demoran más en encontrar empleo...",
        "link": "https://emol.com/otra-url",
    }
    art_fresh = {
        "title": "Nuevo subsidio a la clase media inicia postulaciones",
        "link": "https://biobiochile.cl/noticias/subsidio",
    }

    articles = [art_repeated_url, art_repeated_title, art_fresh]

    filtered = filter_articles_by_history(articles=articles, history=history, days=7, now=now)
    assert len(filtered) == 1
    assert filtered[0]["title"] == "Nuevo subsidio a la clase media inicia postulaciones"

    # Con days=0 (cooldown desactivado), no filtra ningún artículo
    unfiltered = filter_articles_by_history(articles=articles, history=history, days=0, now=now)
    assert len(unfiltered) == 3
