"""Contrato mínimo de los ejemplos revisados del radar."""

import json
from pathlib import Path

from src.analysis.opportunity_eval import Opportunity


CASES_PATH = Path(__file__).parent / "fixtures" / "review_cases.json"


def test_review_cases_cover_diverse_formats_and_uncertainty():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert {case["product_type"] for case in cases} >= {
        "Calculadora", "Simulador", "Juego o desafío", "Guía interactiva", "Utilidad para archivos"
    }
    assert "Pendiente de revisión" in {case["evidence_status"] for case in cases}
    assert "Lista para construir" in {case["evidence_status"] for case in cases}


def test_review_case_values_stay_in_the_supported_contract():
    for case in json.loads(CASES_PATH.read_text(encoding="utf-8")):
        opportunity = Opportunity(
            headline=case["name"], category="Sociedad & Tendencias", why_is_trending="Caso histórico revisado",
            contrarian_or_curious_angle="Comprobar propuesta", suggested_deliverable=case["delivery_format"],
            data_sources=[], virality_score=7, technical_feasibility_score=7,
            fast_execution_strategy="Revisar el caso", product_type=case["product_type"],
            delivery_format=case["delivery_format"], evidence_status=case["evidence_status"],
            share_mechanism=case["share_mechanism"], scope_class=case["scope_class"],
        )
        assert opportunity.evidence_status != "Verificada"
