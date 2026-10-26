"""Pruebas para la comprobación técnica de fuentes propuestas por el LLM."""

from unittest.mock import MagicMock

from src.analysis.opportunity_eval import DataSource, Opportunity
from src.analysis.source_verification import (
    validate_public_http_url,
    verify_opportunity_sources,
)


def _opportunity(*sources: DataSource) -> Opportunity:
    return Opportunity(
        headline="Calculadora de prueba",
        category="Economía & Finanzas",
        why_is_trending="Tema vigente",
        contrarian_or_curious_angle="Comparar escenarios",
        suggested_deliverable="App Interactiva (Streamlit)",
        data_sources=list(sources),
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="1. Obtener datos 2. Calcular 3. Publicar",
    )


def test_validate_public_http_url_rejects_local_and_non_standard_targets():
    assert validate_public_http_url("http://127.0.0.1/internal") == "dirección IP no pública"
    assert validate_public_http_url("https://localhost/data") == "host local no permitido"
    assert validate_public_http_url("https://example.org:8080/data") == "URL con puerto no estándar"
    assert validate_public_http_url("https://example.org:invalido/data") == "URL con puerto inválido"
    assert validate_public_http_url("https://datos.gob.cl/api") is None


def test_verify_opportunity_source_records_successful_http_check():
    source = DataSource(
        name="Portal de datos",
        type="API Pública",
        potential_url_or_query="https://datos.gob.cl/api/serie",
        friction_level="Baja (Horas)",
    )
    response = MagicMock(status_code=200, headers={"content-type": "application/json; charset=utf-8"})
    response.url = source.potential_url_or_query
    request_get = MagicMock(return_value=response)

    assert verify_opportunity_sources(_opportunity(source), request_get=request_get) is True
    assert source.verification_status == "verified"
    assert source.verification_http_status == 200
    assert source.verification_content_type == "application/json"
    assert source.verification_checked_at is not None
    response.close.assert_called_once()
    assert request_get.call_args.kwargs["allow_redirects"] is False
    assert request_get.call_args.kwargs["stream"] is True


def test_verify_opportunity_source_marks_query_and_failed_url_without_calling_query():
    query_source = DataSource(
        name="Búsqueda",
        type="Portal Abierto",
        potential_url_or_query="tarifas eléctricas vigentes Chile",
        friction_level="Baja (Horas)",
    )
    broken_source = DataSource(
        name="Servicio caído",
        type="API Pública",
        potential_url_or_query="https://datos.gob.cl/api/caida",
        friction_level="Baja (Horas)",
    )
    response = MagicMock(status_code=503, headers={"content-type": "application/json"})
    response.url = broken_source.potential_url_or_query
    request_get = MagicMock(return_value=response)

    assert verify_opportunity_sources(
        _opportunity(query_source, broken_source), request_get=request_get
    ) is False
    assert query_source.verification_status == "not_checkable"
    assert broken_source.verification_status == "failed"
    assert broken_source.verification_http_status == 503
    assert request_get.call_count == 1


def test_verify_opportunity_source_reuses_url_check_cache():
    source = DataSource(
        name="Datos",
        type="Dataset Descargable",
        potential_url_or_query="https://datos.gob.cl/serie.csv",
        friction_level="Baja (Horas)",
    )
    response = MagicMock(status_code=200, headers={"content-type": "text/csv"})
    response.url = source.potential_url_or_query
    request_get = MagicMock(return_value=response)
    cache = {}

    assert verify_opportunity_sources(_opportunity(source), request_get=request_get, cache=cache)
    copied_source = source.model_copy()
    assert verify_opportunity_sources(_opportunity(copied_source), request_get=request_get, cache=cache)
    assert request_get.call_count == 1
    assert copied_source.verification_status == "verified"
