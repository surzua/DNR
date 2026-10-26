"""Unit tests for the Opportunity Evaluation module (Step 3)."""

from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch
import pytest

from src.analysis.opportunity_eval import (
    DataSource,
    EvaluationResponseError,
    Opportunity,
    OpportunityAssessment,
    RejectedOpportunity,
    RadarResponse,
    evaluate_opportunities,
    filter_and_rank_opportunities,
)
from src.analysis.prompt_templates import (
    SYSTEM_PROMPT,
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
    assert opp.product_type == "Análisis de datos"
    assert opp.evidence_status == "Pendiente de revisión"
    assert opp.assessment.priority_score() is None

    response = RadarResponse(
        evaluated_topics_count=50,
        top_opportunities=[opp],
    )
    assert response.evaluated_topics_count == 50
    assert len(response.top_opportunities) == 1


def test_gemini_response_schema_has_no_free_form_maps():
    """Gemini Developer API rechaza los esquemas con additionalProperties."""
    assert "additionalProperties" not in json.dumps(RadarResponse.model_json_schema())


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
    prompt = build_evaluation_prompt(
        [art],
        recent_topics=recent_topics,
        lookback_hours=72,
        history_days=5,
    )
    assert "TEMAS Y ÁNGULOS YA ANALIZADOS RECIENTEMENTE" in prompt
    assert "Debate sobre tarifas eléctricas" in prompt
    assert "[1] [EMOL] [Economía]" in prompt
    assert "últimas 72 horas" in prompt
    assert "ÚLTIMOS 5 DÍAS" in prompt
    assert "audience, user_need, first_interaction, user_action" in prompt
    assert "reported_facts" in prompt
    assert "critical_claims" in prompt
    assert "No fuerces un dataset" in SYSTEM_PROMPT
    assert "Rúbrica honesta" in SYSTEM_PROMPT


def test_opportunity_assessment_calculates_weighted_priority():
    assessment = OpportunityAssessment(
        utility_score=5,
        attention_score=4,
        shareability_score=3,
        differentiation_score=2,
        speed_to_publish_score=5,
        durable_value_score=1,
        confidence_score=3,
    )

    assert assessment.has_complete_rubric() is True
    assert assessment.priority_score() == 3.65


def test_filter_and_rank_prefers_complete_product_rubric_over_legacy_scores():
    legacy = Opportunity(
        headline="Más viral, pero sin rúbrica",
        category="Economía & Finanzas",
        why_is_trending="Tema visible",
        contrarian_or_curious_angle="Ángulo",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=10,
        technical_feasibility_score=9,
        fast_execution_strategy="Paso 1, 2, 3",
    )
    assessed = Opportunity(
        headline="Producto mejor fundamentado",
        category="Economía & Finanzas",
        why_is_trending="Tema visible",
        contrarian_or_curious_angle="Ángulo",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Paso 1, 2, 3",
        assessment=OpportunityAssessment(
            utility_score=5,
            attention_score=5,
            shareability_score=5,
            differentiation_score=5,
            speed_to_publish_score=5,
            durable_value_score=5,
            confidence_score=4,
        ),
    )

    ranked = filter_and_rank_opportunities([legacy, assessed])

    assert ranked == [assessed, legacy]


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

    rejected: list[RejectedOpportunity] = []
    filtered = filter_and_rank_opportunities(
        [opp_low_virality, opp_high, opp_low_feasibility, opp_mid],
        min_virality=7,
        min_feasibility=6,
        max_items=3,
        rejected=rejected,
    )

    assert len(filtered) == 2
    # La más alta en puntaje combinado debe ir primero (9+8=17 vs 7+6=13)
    assert filtered[0].headline == "Oportunidad Viral y Factible"
    assert filtered[1].headline == "Oportunidad Justa en Umbral"
    assert {item.reason for item in rejected} == {
        "viralidad_bajo_umbral",
        "factibilidad_bajo_umbral",
    }


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


def test_filter_and_rank_opportunities_intra_run_deduplication():
    """Verifica que si dos oportunidades tienen la misma noticia detonante en una misma corrida, conserve la de mayor score."""
    opp_high = Opportunity(
        headline="Ángulo A (Mayor Score)",
        category="Economía & Finanzas",
        why_is_trending="Tema",
        contrarian_or_curious_angle="Ángulo A",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=9,
        technical_feasibility_score=8,
        fast_execution_strategy="Paso 1, 2, 3",
        trigger_article_title="Personas con estudios universitarios demoran más en encontrar empleo",
        trigger_article_url="https://latercera.com/empleo-2026",
    )
    opp_lower = Opportunity(
        headline="Ángulo B (Menor Score de la misma noticia)",
        category="Economía & Finanzas",
        why_is_trending="Tema",
        contrarian_or_curious_angle="Ángulo B",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=8,
        technical_feasibility_score=7,
        fast_execution_strategy="Paso 1, 2, 3",
        trigger_article_title="Personas con estudios universitarios demoran más en encontrar empleo",
        trigger_article_url="https://latercera.com/empleo-2026",
    )
    opp_other = Opportunity(
        headline="Noticia Diferente",
        category="Sociedad & Tendencias",
        why_is_trending="Tema",
        contrarian_or_curious_angle="Ángulo C",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=7,
        technical_feasibility_score=7,
        fast_execution_strategy="Paso 1, 2, 3",
        trigger_article_title="Lluvias en la zona central",
        trigger_article_url="https://biobiochile.cl/lluvia",
    )

    filtered = filter_and_rank_opportunities([opp_lower, opp_high, opp_other])
    assert len(filtered) == 2
    assert filtered[0].headline == "Ángulo A (Mayor Score)"
    assert filtered[1].headline == "Noticia Diferente"


def test_filter_and_rank_opportunities_excludes_history_triggers():
    """Verifica que descarte oportunidades cuyo detonante coincida con historial reciente."""
    opp = Opportunity(
        headline="Oportunidad con noticia de ayer",
        category="Economía & Finanzas",
        why_is_trending="Tema",
        contrarian_or_curious_angle="Ángulo",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=9,
        technical_feasibility_score=8,
        fast_execution_strategy="Paso 1, 2, 3",
        trigger_article_title="Aluvión en Las Condes deja cortes de luz",
        trigger_article_url="https://latercera.com/nacional/aluvion-las-condes",
    )

    filtered_by_url = filter_and_rank_opportunities(
        [opp],
        exclude_trigger_urls={"latercera.com/nacional/aluvion-las-condes"},
    )
    assert len(filtered_by_url) == 0

    filtered_by_title = filter_and_rank_opportunities(
        [opp],
        exclude_trigger_titles={"aluvion en las condes deja cortes de luz"},
    )
    assert len(filtered_by_title) == 0


def test_filter_and_rank_verifies_trigger_and_minimum_source():
    article = {
        "title": "Ministerio anuncia nueva tarifa eléctrica",
        "link": "https://energia.gob.cl/noticias/tarifa-electrica",
    }
    source = DataSource(
        name="Ministerio de Energía",
        type="Portal Abierto",
        potential_url_or_query="https://energia.gob.cl/tarifas",
        friction_level="Baja (Horas)",
    )
    valid = Opportunity(
        headline="Calculadora de tarifa",
        category="Economía & Finanzas",
        why_is_trending="Nueva tarifa anunciada",
        contrarian_or_curious_angle="Comparar escenarios de consumo",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=[source],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Implementar fórmula",
        trigger_article_title=article["title"],
        trigger_article_url=article["link"],
        evidence_status="Verificada",
    )
    fake_trigger = valid.model_copy(
        update={"headline": "Titular inventado", "trigger_article_title": "Noticia que no fue ingerida"}
    )
    no_source = valid.model_copy(update={"headline": "Sin fuente", "data_sources": []})

    filtered = filter_and_rank_opportunities(
        [fake_trigger, no_source, valid],
        source_articles=[article],
    )

    assert filtered == [valid]
    assert valid.trigger_article_url == article["link"]
    assert valid.evidence_status == "Verificada"


def test_open_product_contract_supports_game_utility_and_downloadable():
    base = dict(
        headline="Desafío de combinaciones",
        category="Deportes",
        why_is_trending="Se acerca una fecha decisiva",
        contrarian_or_curious_angle="Probar escenarios antes del partido",
        suggested_deliverable="Experiencia interactiva",
        data_sources=[DataSource(
            name="Reglamento del torneo",
            type="Regla o reglamento",
            potential_url_or_query="https://ejemplo.cl/reglamento",
            friction_level="Baja (Horas)",
        )],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Leer reglas, implementar escenarios y revisar resultados",
    )
    game = Opportunity(**base, product_type="Juego o desafío", delivery_format="App web")
    utility = Opportunity(**(base | {"headline": "Convertidor", "product_type": "Utilidad para archivos", "suggested_deliverable": "Utilidad local"}))
    downloadable = Opportunity(**(base | {"headline": "Calendario", "product_type": "Recurso descargable", "suggested_deliverable": "Recurso descargable"}))

    assert {game.product_type, utility.product_type, downloadable.product_type} == {
        "Juego o desafío", "Utilidad para archivos", "Recurso descargable"
    }
    assert utility.suggested_deliverable == "Utilidad local"


def test_learning_brief_separates_scope_difficulty_and_validation():
    opp = Opportunity(
        headline="Calculadora de escenarios", category="Economía & Finanzas", why_is_trending="Cambio de tarifa",
        contrarian_or_curious_angle="Comparar consumos", suggested_deliverable="App web", data_sources=[],
        virality_score=8, technical_feasibility_score=8, fast_execution_strategy="Revisar fórmula",
        scope_class="prototipo_breve", minimum_version="Ingresar consumo y ver desglose",
        explicit_limits=["Sin cuentas de usuario"], learning_skill="Validar una fórmula y manejar estado local",
        prior_knowledge="Si no conoces JavaScript, practicar variables y eventos antes.",
        technical_difficulty="baja", verification_effort="alto",
        difficulty_reason="La interfaz es pequeña, pero la tarifa debe contrastarse.",
        manual_steps=["Leer la resolución", "Diseñar entradas", "Probar casos límite"],
        technical_dependencies=["Ninguna: HTML y JavaScript local"],
        validation_cases=["Consumo cero", "Consumo con tramo superior"],
    )
    assert opp.scope_class == "prototipo_breve"
    assert opp.technical_difficulty == "baja"
    assert opp.verification_effort == "alto"
    assert len(opp.validation_cases) == 2


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


def test_evaluate_opportunities_can_require_a_verified_source():
    """Una fuente no accesible excluye la oportunidad antes de que se notifique."""
    source = DataSource(
        name="Fuente directa",
        type="API Pública",
        potential_url_or_query="https://datos.gob.cl/serie.json",
        friction_level="Baja (Horas)",
    )
    opp = Opportunity(
        headline="Oportunidad verificable",
        category="Economía & Finanzas",
        why_is_trending="Tema vigente",
        contrarian_or_curious_angle="Comparar escenarios",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=[source],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Construir MVP",
        trigger_article_title="Nueva medida anunciada",
        trigger_article_url="https://prensa.cl/medida",
    )
    response = MagicMock(parsed=RadarResponse(evaluated_topics_count=1, top_opportunities=[opp]))
    client = MagicMock()
    client.models.generate_content.return_value = response
    source.verification_status = "accessible"

    with patch(
        "src.analysis.opportunity_eval.verify_opportunities_sources",
        return_value={id(opp): True},
    ):
        result = evaluate_opportunities(
            articles=[{"title": "Nueva medida anunciada", "link": "https://prensa.cl/medida"}],
            client=client,
            verify_sources=True,
            require_verified_source=True,
        )

    assert result.top_opportunities == [opp]
    assert result.top_opportunities[0].evidence_status == "Pendiente de revisión"


def test_evaluate_opportunities_records_rejection_when_source_is_not_verified():
    source = DataSource(
        name="Fuente no disponible",
        type="API Pública",
        potential_url_or_query="https://datos.gob.cl/serie.json",
        friction_level="Baja (Horas)",
    )
    opp = Opportunity(
        headline="Oportunidad sin fuente verificable",
        category="Economía & Finanzas",
        why_is_trending="Tema vigente",
        contrarian_or_curious_angle="Comparar escenarios",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=[source],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Construir MVP",
        trigger_article_title="Nueva medida anunciada",
        trigger_article_url="https://prensa.cl/medida",
    )
    response = MagicMock(parsed=RadarResponse(evaluated_topics_count=1, top_opportunities=[opp]))
    client = MagicMock()
    client.models.generate_content.return_value = response

    with patch(
        "src.analysis.opportunity_eval.verify_opportunities_sources",
        return_value={id(opp): False},
    ):
        result = evaluate_opportunities(
            articles=[{"title": "Nueva medida anunciada", "link": "https://prensa.cl/medida"}],
            client=client,
            verify_sources=True,
            require_verified_source=True,
        )

    assert result.top_opportunities == []
    assert result.rejected_opportunities == [
        RejectedOpportunity(opportunity=opp, reason="fuente_url_no_accesible")
    ]


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
        articles=[
            {
                "title": "Autoridades evalúan refuerzo policial",
                "link": "https://latercera.com/seguridad",
            }
        ],
        client=mock_client,
    )

    assert len(res.top_opportunities) == 1
    assert res.top_opportunities[0].headline == "Mapa de delitos comunales vs dotación policial"
    assert res.top_opportunities[0].virality_score == 8


def test_evaluate_opportunities_raises_for_invalid_structured_response():
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = '{"evaluated_topics_count": "not a number"}'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(EvaluationResponseError, match="no cumple el esquema"):
        evaluate_opportunities(
            articles=[{"title": "Noticia", "link": "https://test.cl"}],
            client=mock_client,
        )


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


def test_opportunity_product_fields_are_persisted_in_history():
    opp = Opportunity(
        headline="Calculadora de dividendo",
        category="Economía & Finanzas",
        why_is_trending="Debate por tasas hipotecarias",
        contrarian_or_curious_angle="Comparar el efecto real de una décima en la tasa",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=[],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="Implementar fórmula y escenarios",
        audience="Personas evaluando un crédito hipotecario",
        user_need="Estimar una cuota antes de cotizar",
        user_action="Comparar escenarios de tasa y plazo",
        product_type="Calculadora",
        product_inputs="Monto, pie, tasa y plazo",
        product_output="Cuota estimada y costo total",
        share_reason="Permite comparar una decisión relevante con la familia",
        evidence_status="Fuente localizada",
        validity_note="Actualizar cuando cambien las tasas de referencia",
        known_facts=["La noticia informa ajustes recientes en condiciones hipotecarias."],
        hypotheses_to_test=["Una diferencia pequeña de tasa cambia materialmente la cuota."],
        verification_plan=["Comprobar CAE, seguros incluidos y período de vigencia de cada tasa."],
        distribution_channel="LinkedIn y grupos de personas buscando vivienda",
        existing_alternatives="Simuladores bancarios; este compara escenarios entre entidades.",
        assessment=OpportunityAssessment(
            utility_score=5,
            attention_score=4,
            shareability_score=4,
            differentiation_score=3,
            speed_to_publish_score=5,
            durable_value_score=4,
            confidence_score=3,
        ),
    )

    entry = HistoryEntry.from_opportunity(opp, entry_id="2026-10-06-002")

    assert entry.audience == "Personas evaluando un crédito hipotecario"
    assert entry.product_type == "Calculadora"
    assert entry.product_output == "Cuota estimada y costo total"
    assert entry.evidence_status == "Fuente localizada"
    assert entry.validity_note == "Actualizar cuando cambien las tasas de referencia"
    assert entry.known_facts == ["La noticia informa ajustes recientes en condiciones hipotecarias."]
    assert entry.hypotheses_to_test == ["Una diferencia pequeña de tasa cambia materialmente la cuota."]
    assert entry.verification_plan == ["Comprobar CAE, seguros incluidos y período de vigencia de cada tasa."]
    assert entry.distribution_channel == "LinkedIn y grupos de personas buscando vivienda"
    assert entry.selection_scores["utility_score"] == 5
    assert entry.priority_score == 4.25


def test_evaluate_opportunities_prioritizes_gemini_3_8_flash():
    """Verifica que el modelo por defecto llamado en primera instancia sea gemini-3.8-flash."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = RadarResponse(evaluated_topics_count=5, top_opportunities=[])
    mock_client.models.generate_content.return_value = mock_response

    evaluate_opportunities(
        articles=[{"title": "Test", "link": "https://test.cl"}],
        client=mock_client,
    )

    first_call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert first_call_kwargs["model"] == "gemini-3.8-flash"


def test_evaluate_opportunities_cascades_fallback_on_failure():
    """Verifica que si el primer modelo falla, intente con el siguiente modelo de fallback."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = RadarResponse(evaluated_topics_count=5, top_opportunities=[])

    # El primer intento con gemini-3.8-flash falla (ej. 503), el modelo estable
    # gemini-2.5-flash responde en el segundo intento.
    mock_client.models.generate_content.side_effect = [
        RuntimeError("503 Service Unavailable"),
        mock_response,
    ]

    res = evaluate_opportunities(
        articles=[{"title": "Test", "link": "https://test.cl"}],
        client=mock_client,
    )

    assert mock_client.models.generate_content.call_count == 2
    calls = mock_client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-3.8-flash"
    assert calls[1].kwargs["model"] == "gemini-2.5-flash"
    assert res.evaluated_topics_count == 5


def test_evaluate_opportunities_retries_without_response_schema_on_invalid_argument():
    """La validación local mantiene el contrato si Gemini rechaza el schema."""
    mock_response = MagicMock(parsed=RadarResponse(evaluated_topics_count=5, top_opportunities=[]))
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        RuntimeError("400 INVALID_ARGUMENT"),
        mock_response,
    ]

    result = evaluate_opportunities(
        articles=[{"title": "Test", "link": "https://test.cl"}],
        client=mock_client,
    )

    calls = mock_client.models.generate_content.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["model"] == calls[1].kwargs["model"] == "gemini-3.8-flash"
    assert calls[0].kwargs["config"].response_schema is RadarResponse
    assert calls[1].kwargs["config"].response_schema is None
    assert result.evaluated_topics_count == 5
