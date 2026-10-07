"""Tests for history management and deduplication."""

from datetime import datetime, timezone
from pathlib import Path
from src.storage.history_manager import (
    HistoryEntry,
    generate_next_id,
    get_recent_topics,
    load_history,
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
