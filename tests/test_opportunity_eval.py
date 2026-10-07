"""Unit tests for the Opportunity Evaluation module (Step 3)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from src.analysis.opportunity_eval import (
    DataSource,
    Opportunity,
    RadarResponse,
    evaluate_opportunities,
    filter_and_rank_opportunities,
)
from src.analysis.prompt_templates import (
    build_evaluation_prompt,
    format_article_snippet,
)
from src.ingestion.models import NewsArticle
from src.storage.history_manager import HistoryEntry


def test_opportunity_schemas():
    """Valida la instanciación y validación de los esquemas Pydantic."""
    ds = DataSource(
        name="Mercado Público",
        type="Portal Abierto",
        potential_url_or_query="Licitaciones alumbrado",
        friction_level="Baja (Horas)",
    )
    assert ds.name == "Mercado Público"
    assert ds.type == "Portal Abierto"

    opp = Opportunity(
        headline="Polémica por luminarias públicas",
        category="Política & Estado",
        why_is_trending="Denuncias recientes en municipios",
        contrarian_or_curious_angle="¿Realmente son más caras o aumentó la calidad?",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[ds],
        virality_score=8,
        technical_feasibility_score=7,
        fast_execution_strategy="1. Scrape portal | 2. Limpieza de datos | 3. Scatter plot",
        trigger_article_title="Investigan licitación en comuna de Santiago",
        trigger_article_url="https://latercera.com/noticia/123",
    )
    assert opp.virality_score == 8
    assert opp.trigger_article_title == "Investigan licitación en comuna de Santiago"

    response = RadarResponse(
        evaluated_topics_count=50,
        top_opportunities=[opp],
    )
    assert response.evaluated_topics_count == 50
    assert len(response.top_opportunities) == 1


def test_format_article_snippet_and_build_prompt():
    """Valida que el formateo de artículos para el prompt sea conciso y contenga metadatos."""
    art = NewsArticle(
        title="IPC de septiembre registra variación sorpresiva",
        link="https://emol.com/economia/ipc",
        summary="El Instituto Nacional de Estadísticas dio a conocer hoy los datos de inflación...",
        published_at=datetime.now(timezone.utc),
        source="EMOL",
        category="Economía",
    )
    snippet = format_article_snippet(art, index=1)
    assert "[1] [EMOL] [Economía]" in snippet
    assert "IPC de septiembre" in snippet
    assert "https://emol.com/economia/ipc" in snippet

    recent_topics = ["Debate sobre tarifas eléctricas", "Crisis habitacional en el centro"]
    prompt = build_evaluation_prompt([art], recent_topics=recent_topics)
    assert "TEMAS YA ANALIZADOS EN LOS ÚLTIMOS 7 DÍAS" in prompt
    assert "Debate sobre tarifas eléctricas" in prompt
    assert "[1] [EMOL] [Economía]" in prompt


def test_filter_and_rank_opportunities():
    """Verifica que el filtro determinista elimine candidatos bajo el umbral y ordene por score."""
    opp_high = Opportunity(
        headline="Oportunidad Viral y Factible",
        category="Economía & Finanzas",
        why_is_trending="Tema caliente",
        contrarian_or_curious_angle="Ángulo revelador",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=[],
        virality_score=9,
        technical_feasibility_score=8,
        fast_execution_strategy="Paso 1, 2, 3",
    )
    opp_mid = Opportunity(
        headline="Oportunidad Justa en Umbral",
        category="Deportes",
        why_is_trending="Tema regular",
        contrarian_or_curious_angle="Duda futbolera",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=7,
        technical_feasibility_score=6,
        fast_execution_strategy="Paso 1, 2, 3",
    )
    opp_low_virality = Opportunity(
        headline="Oportunidad con baja viralidad",
        category="Sociedad & Tendencias",
        why_is_trending="Nicho",
        contrarian_or_curious_angle="Dato curioso",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=5,  # < 7
        technical_feasibility_score=8,
        fast_execution_strategy="Paso 1, 2, 3",
    )
    opp_low_feasibility = Opportunity(
        headline="Oportunidad muy difícil de construir",
        category="Política & Estado",
        why_is_trending="Gran escándalo",
        contrarian_or_curious_angle="Investigación profunda",
        suggested_deliverable="Análisis Predictivo/Optimización",
        data_sources=[],
        virality_score=9,
        technical_feasibility_score=4,  # < 6
        fast_execution_strategy="Requiere meses de scraping",
    )

    filtered = filter_and_rank_opportunities(
        [opp_low_virality, opp_high, opp_low_feasibility, opp_mid],
        min_virality=7,
        min_feasibility=6,
        max_items=3,
    )

    assert len(filtered) == 2
    # La más alta en puntaje combinado debe ir primero (9+8=17 vs 7+6=13)
    assert filtered[0].headline == "Oportunidad Viral y Factible"
    assert filtered[1].headline == "Oportunidad Justa en Umbral"


def test_filter_and_rank_opportunities_sanitizes_unsafe_trigger_url():
    opp_unsafe = Opportunity(
        headline="Oportunidad Inyectada",
        category="Economía & Finanzas",
        why_is_trending="Tema",
        contrarian_or_curious_angle="Ángulo",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Paso 1, 2, 3",
        trigger_article_title="Noticia",
        trigger_article_url="javascript:alert(1)",
    )
    filtered = filter_and_rank_opportunities([opp_unsafe])
    assert len(filtered) == 1
    assert filtered[0].trigger_article_url is None


def test_evaluate_opportunities_empty():
    """Verifica que con lista vacía retorne inmediatamente sin llamar a la API."""
    result = evaluate_opportunities(articles=[])
    assert result.evaluated_topics_count == 0
    assert result.top_opportunities == []


def test_evaluate_opportunities_missing_key():
    """Verifica que lance ValueError si no hay API key configurada ni cliente inyectado."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY no encontrada"):
            evaluate_opportunities(
                articles=[{"title": "Noticia de prueba"}],
                api_key=None,
                client=None,
            )


def test_evaluate_opportunities_with_mock_client():
    """Verifica el flujo completo de evaluación estructurada con cliente mockeado."""
    opp = Opportunity(
        headline="Desmitificando el alza del pasaje con datos históricos",
        category="Economía & Finanzas",
        why_is_trending="Debate nacional por subsidios",
        contrarian_or_curious_angle="En términos reales respecto al sueldo mínimo, el pasaje está más bajo que en 2019",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[
            DataSource(
                name="INE",
                type="Dataset Descargable",
                potential_url_or_query="Series históricas IPC",
                friction_level="Baja (Horas)",
            )
        ],
        virality_score=9,
        technical_feasibility_score=8,
        fast_execution_strategy="1. Descargar serie IPC | 2. Normalizar serie histórica | 3. Graficar con matplotlib",
        trigger_article_title="Comisión de Transporte discute nuevo ajuste tarifario",
        trigger_article_url="https://df.cl/tarifas",
    )

    expected_radar = RadarResponse(
        evaluated_topics_count=25,
        top_opportunities=[opp],
    )

    mock_response = MagicMock()
    mock_response.parsed = expected_radar

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    articles = [
        NewsArticle(
            title="Comisión de Transporte discute nuevo ajuste tarifario",
            link="https://df.cl/tarifas",
            summary="Se proyectan ajustes en el transporte público.",
            published_at=datetime.now(timezone.utc),
            source="DF",
        )
    ]

    res = evaluate_opportunities(
        articles=articles,
        client=mock_client,
        min_virality=7,
        min_feasibility=6,
    )

    assert mock_client.models.generate_content.called
    assert res.evaluated_topics_count == 25
    assert len(res.top_opportunities) == 1
    assert res.top_opportunities[0].headline == "Desmitificando el alza del pasaje con datos históricos"
    assert res.top_opportunities[0].trigger_article_url == "https://df.cl/tarifas"


def test_evaluate_opportunities_fallback_json_parsing():
    """Verifica que si response.parsed no está presente, se parsee desde response.text."""
    raw_json = """
    {
      "evaluated_topics_count": 10,
      "top_opportunities": [
        {
          "headline": "Mapa de delitos comunales vs dotación policial",
          "category": "Política & Estado",
          "why_is_trending": "Discusión sobre seguridad",
          "contrarian_or_curious_angle": "¿Tienen más policías las comunas con más denuncias?",
          "suggested_deliverable": "Gráfico Estático de Alto Impacto",
          "data_sources": [
            {
              "name": "CEAD Subdere",
              "type": "Portal Abierto",
              "potential_url_or_query": "Estadísticas delictuales por comuna",
              "friction_level": "Baja (Horas)"
            }
          ],
          "virality_score": 8,
          "technical_feasibility_score": 7,
          "fast_execution_strategy": "Descargar excel CEAD, cruzar con habitantes y plotear ratio",
          "trigger_article_title": "Autoridades evalúan refuerzo policial",
          "trigger_article_url": "https://latercera.com/seguridad"
        }
      ]
    }
    """
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = raw_json

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    res = evaluate_opportunities(
        articles=[{"title": "Noticia de prueba", "link": "https://test.com"}],
        client=mock_client,
    )

    assert len(res.top_opportunities) == 1
    assert res.top_opportunities[0].headline == "Mapa de delitos comunales vs dotación policial"
    assert res.top_opportunities[0].virality_score == 8


def test_history_entry_from_opportunity_with_trigger():
    """Verifica que HistoryEntry capture la información de la noticia detonante."""
    opp = Opportunity(
        headline="Simulador de crédito hipotecario",
        category="Economía & Finanzas",
        why_is_trending="Tasas de interés",
        contrarian_or_curious_angle="Impacto del CAE en evaluación comercial",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=[],
        virality_score=8,
        technical_feasibility_score=7,
        fast_execution_strategy="1. Fórmula cuota | 2. Widget Streamlit",
        trigger_article_title="Bancos ajustan condiciones hipotecarias",
        trigger_article_url="https://df.cl/hipotecarios",
    )

    entry = HistoryEntry.from_opportunity(opp, entry_id="2026-10-06-001")
    assert entry.id == "2026-10-06-001"
    assert entry.topic == "Simulador de crédito hipotecario"
    assert entry.trigger_article_title == "Bancos ajustan condiciones hipotecarias"
    assert entry.trigger_article_url == "https://df.cl/hipotecarios"
