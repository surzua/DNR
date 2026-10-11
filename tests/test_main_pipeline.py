from datetime import datetime, timezone
import sys
from unittest.mock import MagicMock, patch
import pytest

from main import main
from src.analysis.opportunity_eval import Opportunity, RadarResponse
from src.storage.history_manager import HistoryEntry


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


def test_main_missing_gemini_key_exits():
    test_args = ["main.py", "--use-cache"]
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {}, clear=True):
            with patch("main.load_articles_cache", return_value=[]):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1


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
                    with patch("main.save_history") as mock_save:
                        with patch("main.load_history", return_value=[]):
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
                                mock_save.assert_called_once()


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
                    with patch("main.save_history"):
                        with patch("main.load_history", return_value=[]):
                            with patch("main.send_batch_alerts") as mock_batch:
                                main()
                                mock_batch.assert_not_called()


def test_main_with_days_flag_propagates_lookback_hours():
    test_args = ["main.py", "--days", "3", "--skip-llm"]
    with patch.object(sys, "argv", test_args):
        with patch("main.gather_all_sources") as mock_gather:
            with patch("main.save_articles_cache"):
                mock_gather.return_value = []
                main()
                mock_gather.assert_called_once_with(lookback_hours=72)


def test_main_default_days_propagates_24_hours():
    test_args = ["main.py", "--skip-llm"]
    with patch.object(sys, "argv", test_args):
        with patch("main.gather_all_sources") as mock_gather:
            with patch("main.save_articles_cache"):
                mock_gather.return_value = []
                main()
                mock_gather.assert_called_once_with(lookback_hours=24)


def test_main_filters_articles_against_history(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache", "--cooldown-days", "5", "--skip-telegram"]
    radar_resp = RadarResponse(
        evaluated_topics_count=50,
        top_opportunities=[mock_radar_opp],
    )
    art_repeat = MagicMock(source="La Tercera", title="Noticia ya vista", link="https://latercera.com/noticia-vieja")
    art_fresh = MagicMock(source="DF", title="Noticia totalmente nueva", link="https://df.cl/noticia-fresca")

    hist_entry = HistoryEntry(
        id="2026-10-09-001",
        timestamp=datetime.now(timezone.utc),
        topic="Tema viejo",
        category="Economía & Finanzas",
        viral_hook_type="Hook",
        analytical_angle="Angle",
        feasibility_score=8,
        virality_score=8,
        recommended_deliverable="App Interactiva (Streamlit)",
        trigger_article_title="Noticia ya vista",
        trigger_article_url="https://latercera.com/noticia-vieja",
    )

    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[art_repeat, art_fresh]):
                with patch("main.load_history", return_value=[hist_entry]):
                    with patch("main.evaluate_opportunities", return_value=radar_resp) as mock_eval:
                        with patch("main.save_history"):
                            main()
                            mock_eval.assert_called_once()
                            evaluated_articles = mock_eval.call_args.kwargs["articles"]
                            assert len(evaluated_articles) == 1
                            assert evaluated_articles[0].link == "https://df.cl/noticia-fresca"
