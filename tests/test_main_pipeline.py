from datetime import datetime, timezone
import sys
from unittest.mock import MagicMock, patch
import pytest

from main import main
from src.config import PipelineConfig
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


def test_main_manages_publication_lifecycle_without_running_radar():
    entry = HistoryEntry(
        id="2026-10-25-001",
        timestamp=datetime.now(timezone.utc),
        topic="Calculadora de prueba",
        category="Economía & Finanzas",
        viral_hook_type="Hook",
        analytical_angle="Angle",
        feasibility_score=8,
        virality_score=8,
        recommended_deliverable="Calculadora",
    )

    with patch("main.load_history", return_value=[entry]):
        with patch("main.save_history") as mock_save:
            with patch("main.gather_all_sources") as mock_gather:
                with patch.object(sys, "argv", ["main.py", "--mark-selected", entry.id]):
                    assert main() == 0
                assert entry.publication_status == "selected"

                with patch.object(
                    sys,
                    "argv",
                    [
                        "main.py",
                        "--mark-published",
                        entry.id,
                        "--product-url",
                        "https://ejemplo.cl/calculadora",
                        "--publication-notes",
                        "Publicada en LinkedIn",
                    ],
                ):
                    assert main() == 0
                assert entry.publication_status == "published"
                assert entry.product_url == "https://ejemplo.cl/calculadora"

                with patch.object(
                    sys,
                    "argv",
                    [
                        "main.py",
                        "--record-metrics",
                        entry.id,
                        "--visits",
                        "100",
                        "--task-completions",
                        "32",
                        "--hours-invested",
                        "2.5",
                    ],
                ):
                    assert main() == 0

    assert entry.metrics.visits == 100
    assert entry.metrics.task_completions == 32
    assert entry.metrics.hours_invested == 2.5
    assert mock_save.call_count == 3
    mock_gather.assert_not_called()


def test_main_requires_url_when_marking_published():
    with patch.object(sys, "argv", ["main.py", "--mark-published", "2026-10-25-001"]):
        assert main() == 2


def test_main_missing_gemini_key_returns_configuration_error():
    test_args = ["main.py", "--use-cache"]
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {}, clear=True):
            with patch("main.load_articles_cache", return_value=[]):
                assert main() == 2


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
                                mock_save.assert_not_called()


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


def test_main_propagates_effective_pipeline_config(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache", "--skip-telegram"]
    radar_resp = RadarResponse(evaluated_topics_count=1, top_opportunities=[mock_radar_opp])
    pipeline_config = PipelineConfig(
        max_hours_lookback=36,
        history_days_lookback=4,
        max_opportunities_to_notify=2,
        min_virality_score=8,
        min_feasibility_score=7,
    )

    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_pipeline_config", return_value=pipeline_config):
                with patch("main.load_articles_cache", return_value=[]):
                    with patch("main.load_history", return_value=[]):
                        with patch("main.evaluate_opportunities", return_value=radar_resp) as mock_eval:
                            with patch("main.save_history"):
                                assert main() == 0

    assert mock_eval.call_args.kwargs["min_virality"] == 8
    assert mock_eval.call_args.kwargs["min_feasibility"] == 7
    assert mock_eval.call_args.kwargs["max_opportunities"] == 2
    assert mock_eval.call_args.kwargs["lookback_hours"] == 36
    assert mock_eval.call_args.kwargs["history_days"] == 4
    assert mock_eval.call_args.kwargs["verify_sources"] is True
    assert mock_eval.call_args.kwargs["require_verified_source"] is True
    assert mock_eval.call_args.kwargs["source_verification_timeout_seconds"] == 10


def test_main_returns_error_when_evaluation_fails():
    test_args = ["main.py", "--use-cache"]
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[]):
                with patch("main.load_history", return_value=[]):
                    with patch("main.evaluate_opportunities", side_effect=RuntimeError("LLM invalid")):
                        assert main() == 3


def test_main_returns_error_when_telegram_dispatch_fails(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache"]
    radar_resp = RadarResponse(evaluated_topics_count=1, top_opportunities=[mock_radar_opp])
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[]):
                with patch("main.load_history", return_value=[]):
                    with patch("main.evaluate_opportunities", return_value=radar_resp):
                        with patch("main.save_history"):
                            with patch(
                                "main.send_batch_alerts",
                                return_value={
                                    "briefing_sent": True,
                                    "sent": 0,
                                    "failed": 1,
                                    "total": 1,
                                    "skipped": False,
                                },
                            ):
                                assert main() == 4


def test_main_records_individual_delivery_results(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache"]
    radar_resp = RadarResponse(evaluated_topics_count=1, top_opportunities=[mock_radar_opp])
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[]):
                with patch("main.load_history", return_value=[]):
                    with patch("main.evaluate_opportunities", return_value=radar_resp):
                        with patch("main.save_history") as mock_save:
                            with patch(
                                "main.send_batch_alerts",
                                return_value={
                                    "briefing_sent": True,
                                    "sent": 1,
                                    "failed": 0,
                                    "total": 1,
                                    "skipped": False,
                                    "item_results": [True],
                                },
                            ):
                                assert main() == 0

    persisted_history = mock_save.call_args_list[-1].args[0]
    assert persisted_history[0].delivery_status == "delivered"
    assert persisted_history[0].delivery_attempts == 1
    assert persisted_history[0].delivered_at is not None


def test_main_retries_only_pending_delivery(mock_radar_opp: Opportunity):
    test_args = ["main.py", "--use-cache"]
    pending_entry = HistoryEntry.from_opportunity(mock_radar_opp, entry_id="2026-10-25-001")
    radar_resp = RadarResponse(evaluated_topics_count=1, top_opportunities=[])
    with patch.object(sys, "argv", test_args):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            with patch("main.load_articles_cache", return_value=[]):
                with patch("main.load_history", return_value=[pending_entry]):
                    with patch("main.evaluate_opportunities", return_value=radar_resp):
                        with patch("main.save_history") as mock_save:
                            with patch(
                                "main.send_batch_alerts",
                                return_value={
                                    "briefing_sent": True,
                                    "sent": 1,
                                    "failed": 0,
                                    "total": 1,
                                    "skipped": False,
                                    "item_results": [True],
                                },
                            ) as mock_dispatch:
                                assert main() == 0

    assert mock_dispatch.call_args.kwargs["opportunities"] == [pending_entry]
    assert pending_entry.delivery_status == "delivered"
    assert mock_save.call_count == 2


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
