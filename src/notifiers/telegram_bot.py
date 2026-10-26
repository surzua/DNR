"""Despachador y formateador de alertas para Telegram Bot.

Implementa formateo en HTML seguro con sanitización de entidades, fallback automático
a texto plano si la API rechaza entidades, control de tasa (rate-limiting) y modo dry-run.
"""

from datetime import datetime, timezone
import html
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import requests

logger = logging.getLogger("dnr.telegram_bot")

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4096


def is_safe_url(url: Optional[str]) -> bool:
    """Verifica que la URL use un esquema web seguro (http/https) y tenga host válido."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def redact_sensitive_text(text: str, token: Optional[str] = None) -> str:
    """Enmascara tokens y credenciales de Telegram en logs y excepciones de red."""
    if not text:
        return ""
    redacted = text
    if token and len(token) > 5:
        redacted = redacted.replace(token, "[REDACTED_TOKEN]")
    redacted = re.sub(r"/bot[0-9]+:[A-Za-z0-9_-]+", "/bot[REDACTED_TOKEN]", redacted)
    redacted = re.sub(r"/bot[^/\s]+", "/bot[REDACTED_TOKEN]", redacted)
    return redacted


def _extract_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """Extrae un campo de un objeto Pydantic o de un diccionario."""
    if hasattr(obj, field_name):
        val = getattr(obj, field_name)
        return val if val is not None else default
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return default


def _first_text(values: Any) -> Optional[str]:
    """Devuelve el primer texto usable de una lista de notas breves."""
    if not isinstance(values, list):
        return None
    return next(
        (value.strip() for value in values if isinstance(value, str) and value.strip()),
        None,
    )


def _strip_html_tags(text: str) -> str:
    """Elimina etiquetas HTML y restaura entidades comunes para fallback plano."""
    clean = re.sub(r"<[^>]+>", "", text)
    return html.unescape(clean)


def format_briefing_html(
    total_articles: int,
    opportunities_count: int,
    now: Optional[datetime] = None,
) -> str:
    """Genera el mensaje de cabecera (briefing diario) para Telegram en HTML."""
    dt = now or datetime.now(timezone.utc)
    date_str = dt.strftime("%d/%m/%Y %H:%M UTC")

    if opportunities_count == 0:
        return (
            f"📡 <b>DATA NEWSJACKING RADAR</b>\n"
            f"📅 <i>{date_str}</i>\n\n"
            f"📊 <b>Monitoreo:</b> {total_articles} artículos analizados en medios y Reddit.\n"
            f"ℹ️ <b>Sin oportunidades destacadas hoy:</b> Ningún tema superó los filtros mínimos "
            f"de viralidad (≥7) y factibilidad técnica (≥6). No se envían alertas innecesarias."
        )

    return (
        f"📡 <b>DATA NEWSJACKING RADAR</b>\n"
        f"📅 <i>{date_str}</i>\n\n"
        f"📊 <b>Monitoreo:</b> {total_articles} artículos analizados en prensa chilena y Reddit.\n"
        f"🎯 <b>Oportunidades detectadas:</b> {opportunities_count} proyectos viables hoy."
    )


def format_opportunity_html(opportunity: Any) -> str:
    """Formatea una oportunidad individual en HTML estilizado y seguro para Telegram.
    
    Acepta objetos Opportunity (Pydantic), HistoryEntry o diccionarios.
    """
    headline = _extract_field(opportunity, "headline") or _extract_field(opportunity, "topic", "Sin Título")
    category = _extract_field(opportunity, "category", "General")
    virality = _extract_field(opportunity, "virality_score", 0)
    feasibility = _extract_field(
        opportunity,
        "technical_feasibility_score",
        _extract_field(opportunity, "feasibility_score", 0),
    )
    angle = _extract_field(
        opportunity,
        "contrarian_or_curious_angle",
        _extract_field(opportunity, "analytical_angle", ""),
    )
    deliverable = _extract_field(
        opportunity,
        "suggested_deliverable",
        _extract_field(opportunity, "recommended_deliverable", "Análisis exploratorio"),
    )
    strategy = _extract_field(opportunity, "fast_execution_strategy", "")
    trigger_title = _extract_field(opportunity, "trigger_article_title")
    trigger_url = _extract_field(opportunity, "trigger_article_url")
    data_sources = _extract_field(opportunity, "data_sources", [])
    audience = _extract_field(opportunity, "audience")
    user_need = _extract_field(opportunity, "user_need")
    user_action = _extract_field(opportunity, "user_action")
    product_type = _extract_field(opportunity, "product_type")
    product_output = _extract_field(opportunity, "product_output")
    share_reason = _extract_field(opportunity, "share_reason")
    delivery_format = _extract_field(opportunity, "delivery_format")
    first_interaction = _extract_field(opportunity, "first_interaction")
    differentiator = _extract_field(opportunity, "differentiator")
    evidence_status = _extract_field(opportunity, "evidence_status")
    validity_note = _extract_field(opportunity, "validity_note")
    known_fact = _first_text(_extract_field(opportunity, "known_facts", []))
    reported_fact = _first_text(_extract_field(opportunity, "reported_facts", []))
    corroborated_fact = _first_text(_extract_field(opportunity, "corroborated_facts", []))
    assumption = _first_text(_extract_field(opportunity, "assumptions", []))
    hypothesis = _first_text(_extract_field(opportunity, "hypotheses_to_test", []))
    verification_step = _first_text(_extract_field(opportunity, "verification_plan", []))
    distribution_channel = _extract_field(opportunity, "distribution_channel")
    existing_alternatives = _extract_field(opportunity, "existing_alternatives")
    priority_score = _extract_field(opportunity, "priority_score")
    assessment = _extract_field(opportunity, "assessment") or _extract_field(opportunity, "selection_scores")
    confidence_score = _extract_field(assessment, "confidence_score")
    if callable(priority_score):
        priority_score = None
    if priority_score is None and hasattr(assessment, "priority_score"):
        priority_score = assessment.priority_score()

    lines = [
        f"🚀 <b>OPORTUNIDAD DE PRODUCTO</b> (Atención: <b>{virality}/10</b> | Viab: <b>{feasibility}/10</b>)",
        "",
        f"📌 <b>Tema:</b> {html.escape(str(headline), quote=False)}",
        f"📂 <b>Categoría:</b> <i>{html.escape(str(category), quote=False)}</i>",
        "",
        "🎯 <b>Ángulo Analítico / Gancho:</b>",
        f"<i>{html.escape(str(angle), quote=False)}</i>",
    ]

    if product_type or audience or user_need or user_action or product_output:
        lines.extend(["", "🧩 <b>Producto útil:</b>"])
        if product_type:
            lines.append(f"• Tipo: {html.escape(str(product_type), quote=False)}")
        if audience:
            lines.append(f"• Para: {html.escape(str(audience), quote=False)}")
        if user_need:
            lines.append(f"• Necesidad: {html.escape(str(user_need), quote=False)}")
        if user_action:
            lines.append(f"• Acción: {html.escape(str(user_action), quote=False)}")
        if first_interaction:
            lines.append(f"• Primera interacción: {html.escape(str(first_interaction), quote=False)}")
        if product_output:
            lines.append(f"• Resultado: {html.escape(str(product_output), quote=False)}")
        if delivery_format:
            lines.append(f"• Entrega: {html.escape(str(delivery_format), quote=False)}")
        if differentiator:
            lines.append(f"• Diferencia: {html.escape(str(differentiator), quote=False)}")
        if share_reason:
            lines.append(f"• Para compartir: {html.escape(str(share_reason), quote=False)}")
        if evidence_status:
            lines.append(f"• Evidencia: {html.escape(str(evidence_status), quote=False)}")
        if validity_note:
            lines.append(f"• Vigencia: {html.escape(str(validity_note), quote=False)}")

    if known_fact or reported_fact or corroborated_fact or assumption or hypothesis or verification_step or distribution_channel or existing_alternatives:
        lines.extend(["", "🔎 <b>Antes de construir:</b>"])
        if priority_score is not None:
            lines.append(
                f"• Prioridad: {float(priority_score):.2f}/5"
                + (f" | Confianza: {confidence_score}/5" if confidence_score else "")
            )
        if known_fact:
            lines.append(f"• Hecho: {html.escape(known_fact, quote=False)}")
        if reported_fact:
            lines.append(f"• La noticia reporta: {html.escape(reported_fact, quote=False)}")
        if corroborated_fact:
            lines.append(f"• Contrastado: {html.escape(corroborated_fact, quote=False)}")
        if assumption:
            lines.append(f"• Supuesto: {html.escape(assumption, quote=False)}")
        if hypothesis:
            lines.append(f"• Hipótesis: {html.escape(hypothesis, quote=False)}")
        if verification_step:
            lines.append(f"• Verificar: {html.escape(verification_step, quote=False)}")
        if distribution_channel:
            lines.append(f"• Canal: {html.escape(str(distribution_channel), quote=False)}")
        if existing_alternatives:
            lines.append(f"• Diferencia: {html.escape(str(existing_alternatives), quote=False)}")

    lines.extend(["", "📊 <b>Fuentes de Datos Sugeridas:</b>"])

    if data_sources:
        for ds in data_sources:
            name = _extract_field(ds, "name", "Fuente")
            ds_type = _extract_field(ds, "type", "Portal")
            friction = _extract_field(ds, "friction_level", "Baja")
            url_or_q = _extract_field(ds, "potential_url_or_query", "")
            access_status = _extract_field(ds, "verification_status")
            editorial_status = _extract_field(ds, "editorial_status")
            
            ds_line = f"• <b>{html.escape(str(name), quote=False)}</b> ({html.escape(str(ds_type), quote=False)} | Fricción: {html.escape(str(friction), quote=False)})"
            if url_or_q:
                ds_line += f"\n  ↳ <code>{html.escape(str(url_or_q), quote=False)}</code>"
            if access_status == "accessible":
                ds_line += "\n  ↳ URL accesible; contenido pendiente de revisión editorial"
            elif access_status == "failed":
                ds_line += "\n  ↳ URL no accesible en la comprobación técnica"
            if editorial_status and editorial_status != "pending_review":
                ds_line += f"\n  ↳ Estado editorial: {html.escape(str(editorial_status), quote=False)}"
            lines.append(ds_line)
    else:
        lines.append("• Datos públicos en portales de transparencia / Wikipedia")

    lines.extend([
        "",
        f"⏱️ <b>Entregable:</b> {html.escape(str(deliverable), quote=False)}",
    ])

    if strategy:
        lines.extend([
            "",
            "🛠️ <b>Primeros pasos:</b>",
            f"{html.escape(str(strategy), quote=False)}",
        ])

    if trigger_title:
        lines.append("")
        if trigger_url and is_safe_url(trigger_url):
            lines.append(
                f"📰 <b>Noticia Detonante:</b> <a href=\"{html.escape(str(trigger_url).strip(), quote=True)}\">"
                f"{html.escape(str(trigger_title), quote=False)}</a>"
            )
        else:
            lines.append(f"📰 <b>Noticia Detonante:</b> {html.escape(str(trigger_title), quote=False)}")

    message = "\n".join(lines)
    
    # Prevenir desbordamiento del límite estricto de Telegram
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning("Mensaje de oportunidad excedió %d caracteres. Truncando...", MAX_MESSAGE_LENGTH)
        message = message[: MAX_MESSAGE_LENGTH - 20] + "\n[... Truncado]"
        
    return message


def _has_valid_credentials(token: Optional[str], chat: Optional[str]) -> bool:
    """Verifica si las credenciales de Telegram existen y no son placeholders."""
    if not token or not chat:
        return False
    if "your_telegram" in token.lower() or "your_telegram" in chat.lower():
        return False
    return True


def send_telegram_message(
    text: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    timeout: int = 10,
    disable_web_page_preview: bool = True,
) -> bool:
    """Envía un mensaje individual a través de la API oficial de Telegram.
    
    Si el envío en HTML falla por parseo de entidades (HTTP 400), automáticamente
    ejecuta un fallback reintentando el envío en texto plano sin etiquetas.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not _has_valid_credentials(token, chat):
        logger.warning(
            "Credenciales de Telegram no configuradas o con valor por defecto. "
            "Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env para activar el envío real."
        )
        return False

    url = TELEGRAM_API_URL.format(token=token)
    payload: Dict[str, Any] = {
        "chat_id": chat,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        if response.status_code == 200:
            logger.debug("Mensaje enviado con éxito a Telegram (chat_id: %s).", chat)
            return True

        # Error 400 por sintaxis de entidades HTML -> Fallback a texto plano
        if response.status_code == 400 and parse_mode:
            resp_json = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            desc = resp_json.get("description", response.text)
            logger.warning(
                "Telegram rechazó el parseo de entidades (%s). Activando fallback a texto plano...",
                desc,
            )
            plain_text = _strip_html_tags(text)
            fallback_payload = {
                "chat_id": chat,
                "text": plain_text,
                "disable_web_page_preview": disable_web_page_preview,
            }
            fallback_res = requests.post(url, json=fallback_payload, timeout=timeout)
            if fallback_res.status_code == 200:
                logger.info("Fallback de texto plano enviado exitosamente.")
                return True
            logger.error(
                "Error también en fallback de Telegram: HTTP %d - %s",
                fallback_res.status_code,
                redact_sensitive_text(fallback_res.text, token=token),
            )
            return False

        logger.error(
            "Error al enviar mensaje a Telegram: HTTP %d - %s",
            response.status_code,
            redact_sensitive_text(response.text, token=token),
        )
        return False

    except requests.exceptions.Timeout:
        logger.error("Timeout al intentar conectar con la API de Telegram (%ds).", timeout)
        return False
    except requests.exceptions.RequestException as e:
        safe_msg = redact_sensitive_text(str(e), token=token)
        logger.error("Error de conexión de red con Telegram: %s", safe_msg)
        return False
    except Exception as e:
        safe_msg = redact_sensitive_text(str(e), token=token)
        logger.error("Excepción inesperada al enviar mensaje a Telegram: %s", safe_msg)
        return False


def send_telegram_alert(
    opportunity: Any,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """Envía una oportunidad individual formateada a Telegram."""
    formatted_html = format_opportunity_html(opportunity)

    if dry_run:
        logger.info("[DRY-RUN] Simulación de alerta a Telegram:\n%s\n", formatted_html)
        return True

    return send_telegram_message(
        text=formatted_html,
        bot_token=bot_token,
        chat_id=chat_id,
        parse_mode="HTML",
    )


def send_batch_alerts(
    opportunities: List[Any],
    total_articles: int = 0,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    dry_run: bool = False,
    delay_between_messages: float = 0.5,
) -> Dict[str, Any]:
    """Envía el briefing diario y el lote de oportunidades con control de tasa.
    
    Retorna estadísticas de despacho y ``item_results`` en el mismo orden que
    ``opportunities`` para que el historial pueda persistir cada resultado.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not dry_run and not _has_valid_credentials(token, chat):
        logger.warning(
            "TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados (o tienen valores por defecto). "
            "Omitiendo despacho a Telegram."
        )
        return {
            "briefing_sent": False,
            "sent": 0,
            "failed": len(opportunities),
            "total": len(opportunities),
            "skipped": True,
            "item_results": [],
        }

    # 1. Enviar mensaje de cabecera / briefing
    briefing_html = format_briefing_html(
        total_articles=total_articles,
        opportunities_count=len(opportunities),
    )

    if dry_run:
        logger.info("[DRY-RUN] Simulación de cabecera Briefing:\n%s\n", briefing_html)
        briefing_ok = True
    else:
        briefing_ok = send_telegram_message(
            text=briefing_html,
            bot_token=token,
            chat_id=chat,
            parse_mode="HTML",
        )

    # Si no hay oportunidades, el briefing ya informó el estado y terminamos
    if not opportunities:
        return {
            "briefing_sent": briefing_ok,
            "sent": 0,
            "failed": 0,
            "total": 0,
            "skipped": False,
            "item_results": [],
        }

    # 2. Despachar cada oportunidad con pausa para evitar rate-limits
    sent_count = 0
    failed_count = 0
    item_results: List[bool] = []

    for i, opp in enumerate(opportunities, start=1):
        if not dry_run and delay_between_messages > 0:
            time.sleep(delay_between_messages)

        logger.info("Despachando alerta %d/%d a Telegram...", i, len(opportunities))
        ok = send_telegram_alert(
            opportunity=opp,
            bot_token=token,
            chat_id=chat,
            dry_run=dry_run,
        )
        if ok:
            sent_count += 1
        else:
            failed_count += 1
        item_results.append(ok)

    logger.info(
        "Despacho a Telegram completado: %d enviadas, %d fallidas (Total: %d)",
        sent_count,
        failed_count,
        len(opportunities),
    )

    return {
        "briefing_sent": briefing_ok,
        "sent": sent_count,
        "failed": failed_count,
        "total": len(opportunities),
        "skipped": False,
        "item_results": item_results,
    }
