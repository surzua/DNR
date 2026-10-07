"""Tests unitarios para la capa de notificaciones de Telegram Bot."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
import requests

from src.analysis.opportunity_eval import DataSource, Opportunity
from src.notifiers.telegram_bot import (
    _strip_html_tags,
    format_briefing_html,
    format_opportunity_html,
    is_safe_url,
    redact_sensitive_text,
    send_batch_alerts,
    send_telegram_alert,
    send_telegram_message,
)
from src.storage.history_manager import HistoryEntry


@pytest.fixture
def sample_opportunity() -> Opportunity:
    return Opportunity(
        headline="¿Subieron los arriendos o bajó el metraje?",
        category="Economía & Finanzas",
        why_is_trending="Debate sobre acceso a la vivienda en Santiago",
        contrarian_or_curious_angle="Aunque el precio nominal parece estancado, el costo por m² subió un 25%.",
        suggested_deliverable="Gráfico Estático de Alto Impacto",
        data_sources=[
            DataSource(
                name="Portales Inmobiliarios",
                type="Scraping HTML",
                potential_url_or_query="https://ejemplo.cl/arriendos",
                friction_level="Baja (Horas)",
            ),
            DataSource(
                name="INE Chile",
                type="Portal Abierto",
                potential_url_or_query="Estadísticas de edificación",
                friction_level="Media (1-2 días)",
            ),
        ],
        virality_score=9,
        technical_feasibility_score=8,
        fast_execution_strategy="1. Scrapear 500 avisos. 2. Calcular precio/m2. 3. Boxplot comparativo.",
        trigger_article_title="Precios de arriendos en Santiago marcan leve retroceso en septiembre",
        trigger_article_url="https://ejemplo.com/noticias/arriendos-septiembre",
    )


def test_strip_html_tags():
    raw_html = "<b>Hola</b> &amp; <i>Mundo</i> &lt;test&gt; <a href='url'>Link</a>"
    plain = _strip_html_tags(raw_html)
    assert plain == "Hola & Mundo <test> Link"


def test_format_briefing_html_with_opportunities():
    fixed_dt = datetime(2026, 10, 7, 10, 30, tzinfo=timezone.utc)
    briefing = format_briefing_html(
        total_articles=250,
        opportunities_count=3,
        now=fixed_dt,
    )
    assert "DATA NEWSJACKING RADAR" in briefing
    assert "07/10/2026 10:30 UTC" in briefing
    assert "250 artículos analizados" in briefing
    assert "3 proyectos viables hoy" in briefing


def test_format_briefing_html_zero_opportunities():
    fixed_dt = datetime(2026, 10, 7, 10, 30, tzinfo=timezone.utc)
    briefing = format_briefing_html(
        total_articles=180,
        opportunities_count=0,
        now=fixed_dt,
    )
    assert "Sin oportunidades destacadas hoy" in briefing
    assert "180 artículos" in briefing


def test_format_opportunity_html_structure_and_escaping(sample_opportunity: Opportunity):
    # Agregar caracteres especiales para validar el escapado seguro en HTML
    sample_opportunity.headline = "Arriendos <en alza> & 'polémica'"
    formatted = format_opportunity_html(sample_opportunity)

    assert "Arriendos &lt;en alza&gt; &amp; 'polémica'" in formatted
    assert "Economía &amp; Finanzas" in formatted
    assert "Viral: <b>9/10</b>" in formatted
    assert "Viab: <b>8/10</b>" in formatted
    assert "https://ejemplo.com/noticias/arriendos-septiembre" in formatted
    assert "Precios de arriendos en Santiago marcan leve retroceso" in formatted
    assert "<b>Portales Inmobiliarios</b>" in formatted
    assert "<code>https://ejemplo.cl/arriendos</code>" in formatted


def test_format_opportunity_html_from_history_entry():
    entry = HistoryEntry(
        id="2026-10-07-001",
        timestamp=datetime.now(timezone.utc),
        topic="Crisis de Luminarias",
        category="Política & Estado",
        viral_hook_type="Contrarian / Curious Hook",
        analytical_angle="Comparativa comunal",
        data_sources=[{"name": "Mercado Público", "type": "API Pública", "friction_level": "Baja"}],
        feasibility_score=7,
        virality_score=8,
        recommended_deliverable="App Interactiva (Streamlit)",
        fast_execution_strategy="1. API 2. App",
        trigger_article_title="Contraloría detecta irregularidades",
        trigger_article_url="https://noticia.cl/luminarias",
        status="candidate",
    )
    formatted = format_opportunity_html(entry)
    assert "Crisis de Luminarias" in formatted
    assert "Viral: <b>8/10</b>" in formatted
    assert "Viab: <b>7/10</b>" in formatted
    assert "Mercado Público" in formatted


def test_format_opportunity_html_truncation():
    giant_opp = {
        "headline": "Titular Normal",
        "category": "General",
        "virality_score": 8,
        "technical_feasibility_score": 8,
        "contrarian_or_curious_angle": "A" * 5000,
    }
    formatted = format_opportunity_html(giant_opp)
    assert len(formatted) <= 4096
    assert "[... Truncado]" in formatted


@patch("src.notifiers.telegram_bot.requests.post")
def test_send_telegram_message_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    ok = send_telegram_message(
        text="<b>Mensaje de prueba</b>",
        bot_token="test_token",
        chat_id="123456",
        parse_mode="HTML",
    )

    assert ok is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "https://api.telegram.org/bottest_token/sendMessage" in args[0]
    assert kwargs["json"]["chat_id"] == "123456"
    assert kwargs["json"]["text"] == "<b>Mensaje de prueba</b>"
    assert kwargs["json"]["parse_mode"] == "HTML"


def test_send_telegram_message_missing_credentials():
    with patch.dict("os.environ", {}, clear=True):
        ok = send_telegram_message(
            text="Test",
            bot_token=None,
            chat_id=None,
        )
        assert ok is False


@patch("src.notifiers.telegram_bot.requests.post")
def test_send_telegram_message_fallback_on_400_bad_entity(mock_post):
    # Primera llamada falla con 400 Bad Request (entidades)
    resp_400 = MagicMock()
    resp_400.status_code = 400
    resp_400.headers = {"content-type": "application/json"}
    resp_400.json.return_value = {"description": "Bad Request: can't parse entities"}

    # Segunda llamada (fallback en texto plano) triunfa con 200
    resp_200 = MagicMock()
    resp_200.status_code = 200

    mock_post.side_effect = [resp_400, resp_200]

    ok = send_telegram_message(
        text="<b>Titular</b> con error de tag",
        bot_token="test_token",
        chat_id="123456",
        parse_mode="HTML",
    )

    assert ok is True
    assert mock_post.call_count == 2
    # En la segunda llamada debe haber enviado texto plano sin etiquetas
    second_call_kwargs = mock_post.call_args_list[1][1]
    assert "<b>" not in second_call_kwargs["json"]["text"]
    assert "parse_mode" not in second_call_kwargs["json"]


@patch("src.notifiers.telegram_bot.requests.post")
def test_send_telegram_message_http_error(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_post.return_value = mock_resp

    ok = send_telegram_message(
        text="Test",
        bot_token="invalid_token",
        chat_id="123",
    )
    assert ok is False


@patch("src.notifiers.telegram_bot.requests.post")
def test_send_telegram_message_timeout(mock_post):
    mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
    ok = send_telegram_message(
        text="Test",
        bot_token="token",
        chat_id="123",
    )
    assert ok is False


def test_send_telegram_alert_dry_run(sample_opportunity: Opportunity):
    with patch("src.notifiers.telegram_bot.requests.post") as mock_post:
        ok = send_telegram_alert(
            opportunity=sample_opportunity,
            bot_token="token",
            chat_id="123",
            dry_run=True,
        )
        assert ok is True
        mock_post.assert_not_called()


def test_send_batch_alerts_dry_run(sample_opportunity: Opportunity):
    opps = [sample_opportunity, sample_opportunity]
    results = send_batch_alerts(
        opportunities=opps,
        total_articles=150,
        bot_token="token",
        chat_id="123",
        dry_run=True,
        delay_between_messages=0,
    )

    assert results["briefing_sent"] is True
    assert results["sent"] == 2
    assert results["failed"] == 0
    assert results["total"] == 2
    assert results["skipped"] == False


def test_send_batch_alerts_missing_credentials(sample_opportunity: Opportunity):
    with patch.dict("os.environ", {}, clear=True):
        results = send_batch_alerts(
            opportunities=[sample_opportunity],
            total_articles=50,
            bot_token=None,
            chat_id=None,
            dry_run=False,
        )
        assert results["skipped"] is True
        assert results["sent"] == 0


@patch("src.notifiers.telegram_bot.requests.post")
def test_send_batch_alerts_live_mocked(mock_post, sample_opportunity: Opportunity):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    results = send_batch_alerts(
        opportunities=[sample_opportunity],
        total_articles=100,
        bot_token="valid_token",
        chat_id="999",
        dry_run=False,
        delay_between_messages=0,
    )

    assert results["briefing_sent"] is True
    assert results["sent"] == 1
    assert results["failed"] == 0
    assert mock_post.call_count == 2  # 1 briefing + 1 oportunidad


def test_is_safe_url():
    assert is_safe_url("https://latercera.com/noticia") is True
    assert is_safe_url("http://df.cl/economia") is True
    assert is_safe_url("javascript:alert(1)") is False
    assert is_safe_url("tg://resolve?domain=test") is False
    assert is_safe_url("data:text/html,<h1>test</h1>") is False
    assert is_safe_url("") is False
    assert is_safe_url(None) is False
    assert is_safe_url("just-a-string") is False


def test_format_opportunity_html_rejects_unsafe_trigger_url(sample_opportunity: Opportunity):
    sample_opportunity.trigger_article_url = "javascript:alert('XSS')"
    formatted = format_opportunity_html(sample_opportunity)
    assert "<a href=\"javascript:" not in formatted
    assert "Precios de arriendos en Santiago marcan leve retroceso" in formatted


def test_redact_sensitive_text():
    secret_token = "123456789:ABCDefGhIjKlMnOpQrStUvWxYz"
    raw_error = f"HTTPSConnectionPool: Max retries exceeded with url: /bot{secret_token}/sendMessage"
    redacted = redact_sensitive_text(raw_error, token=secret_token)
    assert secret_token not in redacted
    assert "[REDACTED_TOKEN]" in redacted


@patch("src.notifiers.telegram_bot.logger.error")
@patch("src.notifiers.telegram_bot.requests.post")
def test_send_telegram_message_redacts_token_on_network_error(mock_post, mock_logger_error):
    token = "987654321:SECRET_TOKEN_XYZ"
    mock_post.side_effect = requests.exceptions.RequestException(
        f"Failed to connect: https://api.telegram.org/bot{token}/sendMessage"
    )

    ok = send_telegram_message(
        text="Test",
        bot_token=token,
        chat_id="123",
    )
    assert ok is False
    mock_logger_error.assert_called_once()
    logged_msg = mock_logger_error.call_args[0][1]
    assert token not in logged_msg
    assert "[REDACTED_TOKEN]" in logged_msg
