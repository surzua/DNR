"""Integration tests for main.py execution and CLI flags."""

import sys
from unittest.mock import MagicMock, patch
import pytest

from main import main
from src.analysis.opportunity_eval import Opportunity, RadarResponse


@pytest.fixture
def mock_radar_opp() -> Opportunity:
    return Opportunity(
        headline="Oportunidad de prueba",
        category="Economía & Finanzas",
        why_is_trending="Tema en tendencia",
        contrarian_or_curious_angle="Ángulo curioso",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[],
        virality_score=8,
        technical_feasibility_score=8,
        fast_execution_strategy="1. Datos 2. Graficar 3. Publicar",
    )


def test_main_with_skip_llm():
    test_args = ["main.py", "--use-cache", "--skip-llm"]
    with patch.object(sys, "argv", test_args):
        with patch("main.load_articles_cache", return_value=[]):
            with patch("main.gather_all_sources", return_value=[]):
                with patch("main.evaluate_opportunities") as mock_eval:
                    main()
                    mock_eval.assert_not_called()


def test_main_with_dry_run_and_opportunities(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache", "--dry-run"]
    radar_resp = RadarResponse(
        evaluated_topics_count=50,
        top_opportunities=[mock_radar_opp],
    )
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[MagicMock(source="La Tercera")]):
                with patch("main.evaluate_opportunities", return_value=radar_resp):
                    with patch("main.send_batch_alerts") as mock_batch:
                        mock_batch.return_value = {
                            "briefing_sent": True,
                            "sent": 1,
                            "failed": 0,
                            "total": 1,
                        }
                        main()
                        mock_batch.assert_called_once()
                        assert mock_batch.call_args.kwargs["dry_run"] is True


def test_main_with_skip_telegram(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache", "--skip-telegram"]
    radar_resp = RadarResponse(
        evaluated_topics_count=50,
        top_opportunities=[mock_radar_opp],
    )
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[MagicMock(source="La Tercera")]):
                with patch("main.evaluate_opportunities", return_value=radar_resp):
                    with patch("main.send_batch_alerts") as mock_batch:
                        main()
                        mock_batch.assert_not_called()
