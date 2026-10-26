"""Data Newsjacking Radar (DNR) - Pipeline Entrypoint."""

import argparse
from collections import Counter
import logging
import os
import sys
from dotenv import load_dotenv

from src.analysis import evaluate_opportunities
from src.config import PipelineConfigError, load_pipeline_config
from src.ingestion import gather_all_sources
from src.notifiers import send_batch_alerts
from src.storage import (
    HistoryEntry,
    find_history_entry,
    filter_articles_by_history,
    generate_next_id,
    get_entries_pending_delivery,
    get_publication_report,
    get_rejection_report,
    get_recent_topics,
    get_recent_trigger_titles,
    get_recent_trigger_urls,
    load_articles_cache,
    load_history,
    save_articles_cache,
    save_history,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("dnr.main")

EXIT_SUCCESS = 0
EXIT_CONFIGURATION_ERROR = 2
EXIT_EVALUATION_ERROR = 3
EXIT_NOTIFICATION_ERROR = 4


def _dispatch_succeeded(dispatch_results: dict) -> bool:
    """Determina si Telegram completó el briefing y todas las alertas requeridas."""
    return (
        not dispatch_results.get("skipped", False)
        and dispatch_results.get("briefing_sent", False)
        and dispatch_results.get("failed", 0) == 0
    )


def _handle_publication_command(args: argparse.Namespace) -> int:
    """Ejecuta operaciones locales del ciclo de vida de una oportunidad."""
    metric_values = {
        "visits": args.visits,
        "task_completions": args.task_completions,
        "share_clicks": args.share_clicks,
        "corrections": args.corrections,
        "hours_invested": args.hours_invested,
    }

    if args.publication_report:
        try:
            report = get_publication_report(load_history(), days=args.report_days)
        except ValueError as exc:
            logger.error("Parámetros inválidos para el reporte: %s", exc)
            return EXIT_CONFIGURATION_ERROR
        logger.info(
            "Reporte de publicación (%d días): %d publicadas, %d seleccionadas, %d archivadas | "
            "%d visitas, %d resultados completados, %d clics para compartir, %d correcciones, %.1f horas.",
            report["days"],
            report["published"],
            report["selected"],
            report["archived"],
            report["visits"],
            report["task_completions"],
            report["share_clicks"],
            report["corrections"],
            report["hours_invested"],
        )
        for entry in report["published_entries"]:
            logger.info("  • %s | %s | %s", entry.id, entry.topic, entry.product_url or "sin URL")
        return EXIT_SUCCESS

    if args.rejection_report:
        try:
            report = get_rejection_report(load_history(), days=args.report_days)
        except ValueError as exc:
            logger.error("Parámetros inválidos para el reporte: %s", exc)
            return EXIT_CONFIGURATION_ERROR
        logger.info(
            "Reporte de descartes (%d días): %d candidatos descartados.",
            report["days"],
            report["rejected"],
        )
        for reason, count in sorted(report["reasons"].items()):
            logger.info("  • %s: %d", reason, count)
        for entry in report["entries"]:
            logger.info("  ↳ %s | %s | %s", entry.id, entry.topic, entry.rejection_reason)
        return EXIT_SUCCESS

    entry_id = args.mark_selected or args.mark_published or args.mark_archived or args.record_metrics
    if not entry_id:
        logger.error("Indica una acción de ciclo de publicación antes de usar sus parámetros.")
        return EXIT_CONFIGURATION_ERROR
    if args.product_url and not args.mark_published:
        logger.error("--product-url solo puede usarse junto con --mark-published.")
        return EXIT_CONFIGURATION_ERROR
    if args.mark_published and not args.product_url:
        logger.error("--mark-published requiere --product-url con la URL pública de la herramienta.")
        return EXIT_CONFIGURATION_ERROR
    if any(value is not None for value in metric_values.values()) and not args.record_metrics:
        logger.error("Las métricas solo pueden actualizarse junto con --record-metrics ID.")
        return EXIT_CONFIGURATION_ERROR
    if args.record_metrics and all(value is None for value in metric_values.values()):
        logger.error("--record-metrics requiere al menos una métrica.")
        return EXIT_CONFIGURATION_ERROR

    history = load_history()
    entry = find_history_entry(history, entry_id)
    if entry is None:
        logger.error("No existe una oportunidad con ID %s.", entry_id)
        return EXIT_CONFIGURATION_ERROR
    if entry.evaluation_status != "accepted":
        logger.error(
            "La oportunidad %s fue descartada (%s) y no puede pasar al ciclo de publicación.",
            entry_id,
            entry.rejection_reason or "sin motivo registrado",
        )
        return EXIT_CONFIGURATION_ERROR
    if args.record_metrics and entry.published_at is None:
        logger.error("La oportunidad %s aún no está publicada; no se pueden registrar métricas de uso.", entry_id)
        return EXIT_CONFIGURATION_ERROR

    try:
        if args.mark_selected:
            entry.mark_selected()
            action = "seleccionada para producción"
        elif args.mark_published:
            entry.mark_published(args.product_url, notes=args.publication_notes)
            action = "marcada como publicada"
        elif args.mark_archived:
            entry.mark_archived(notes=args.publication_notes)
            action = "archivada"
        else:
            entry.update_metrics(**metric_values)
            action = "métricas actualizadas"
        save_history(history)
    except ValueError as exc:
        logger.error("No se pudo actualizar %s: %s", entry_id, exc)
        return EXIT_CONFIGURATION_ERROR
    except Exception as exc:
        logger.exception("No se pudo guardar el ciclo de publicación: %s", exc)
        return EXIT_EVALUATION_ERROR

    logger.info("Oportunidad %s %s.", entry_id, action)
    return EXIT_SUCCESS


def main() -> int:
    """Ejecuta el pipeline principal de Data Newsjacking Radar."""
    parser = argparse.ArgumentParser(description="Data Newsjacking Radar (DNR)")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Ventana de días hacia atrás para recolectar noticias (ej: 1, 3, 7). Por defecto usa pipeline.max_hours_lookback.",
    )
    parser.add_argument(
        "--cooldown-days",
        type=int,
        default=None,
        help="Días de gracia para evitar repetir noticias que ya generaron oportunidades. Por defecto usa pipeline.history_days_lookback; 0 desactiva el filtro.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Modelo de Gemini a utilizar (por defecto gemini-3.8-flash con fallbacks automáticos)",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Carga los artículos desde el snapshot local data/latest_articles.json si existe",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Omite la fase de evaluación con Gemini LLM",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el despacho a Telegram mostrando los mensajes formateados en consola sin enviarlos a la red",
    )
    parser.add_argument(
        "--skip-telegram",
        action="store_true",
        help="Omite la fase de despacho de notificaciones a Telegram",
    )
    lifecycle_group = parser.add_mutually_exclusive_group()
    lifecycle_group.add_argument(
        "--mark-selected",
        metavar="ID",
        help="Marca una oportunidad como elegida para producción",
    )
    lifecycle_group.add_argument(
        "--mark-published",
        metavar="ID",
        help="Marca una oportunidad como publicada; requiere --product-url",
    )
    lifecycle_group.add_argument(
        "--mark-archived",
        metavar="ID",
        help="Archiva una oportunidad o producto que ya no se mantendrá",
    )
    lifecycle_group.add_argument(
        "--record-metrics",
        metavar="ID",
        help="Actualiza los totales observados de una oportunidad publicada",
    )
    lifecycle_group.add_argument(
        "--publication-report",
        action="store_true",
        help="Muestra un resumen de publicaciones y métricas",
    )
    lifecycle_group.add_argument(
        "--rejection-report",
        action="store_true",
        help="Muestra candidatos descartados y los motivos registrados",
    )
    parser.add_argument("--product-url", help="URL pública HTTP(S) de la herramienta publicada")
    parser.add_argument("--publication-notes", help="Notas de contexto, distribución o mantenimiento")
    parser.add_argument("--visits", type=int, help="Total de visitas o sesiones observado")
    parser.add_argument("--task-completions", type=int, help="Total de personas que llegaron al resultado")
    parser.add_argument("--share-clicks", type=int, help="Total de clics para compartir o copiar enlace")
    parser.add_argument("--corrections", type=int, help="Total de correcciones o incidencias detectadas")
    parser.add_argument("--hours-invested", type=float, help="Horas reales invertidas en la pieza")
    parser.add_argument(
        "--report-days",
        type=int,
        default=7,
        help="Días incluidos por --publication-report (por defecto: 7)",
    )
    args = parser.parse_args()

    if any(
        (
            args.mark_selected,
            args.mark_published,
            args.mark_archived,
            args.record_metrics,
            args.publication_report,
            args.rejection_report,
            args.product_url,
            args.publication_notes,
            args.visits is not None,
            args.task_completions is not None,
            args.share_clicks is not None,
            args.corrections is not None,
            args.hours_invested is not None,
        )
    ):
        return _handle_publication_command(args)

    try:
        pipeline_config = load_pipeline_config()
    except PipelineConfigError as exc:
        logger.error("Configuración inválida del pipeline: %s", exc)
        return EXIT_CONFIGURATION_ERROR

    lookback_hours = (
        max(1, args.days) * 24
        if args.days is not None
        else pipeline_config.max_hours_lookback
    )
    lookback_days = (lookback_hours + 23) // 24

    logger.info("==================================================")
    logger.info("Iniciando Data Newsjacking Radar (DNR)")
    if lookback_days > 1:
        logger.info("Ventana extendida de ingesta: %d días (%d horas hacia atrás)", lookback_days, lookback_hours)
    logger.info("==================================================")

    # Fase 1: Ingesta de fuentes (Prensa RSS + Reddit) o carga desde cache
    if args.use_cache:
        logger.info("Modo desarrollo: Intentando cargar artículos desde cache local...")
        articles = load_articles_cache()
        if not articles:
            logger.info("Cache vacío o no encontrado. Ejecutando recolección en vivo...")
            articles = gather_all_sources(lookback_hours=lookback_hours)
            save_articles_cache(articles)
    else:
        articles = gather_all_sources(lookback_hours=lookback_hours)
        # Guardar snapshot local (ignorado en Git) para inspección y depuración
        save_articles_cache(articles)

    logger.info("Fase de Ingesta finalizada: %d artículos disponibles", len(articles))

    # Resumen por fuente
    counts = Counter(a.source for a in articles)
    for source_name, count in counts.most_common():
        logger.info("  • %s: %d artículos", source_name, count)

    # Fase 2 y 3: Evaluación de oportunidades con Gemini Flash
    if args.skip_llm:
        logger.info("Bandera --skip-llm activa: Omitiendo fase de evaluación LLM.")
        return EXIT_SUCCESS

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.error(
            "GEMINI_API_KEY no encontrada en variables de entorno o archivo .env. "
            "Para ejecutar la evaluación de oportunidades, configura tu API key en .env. "
            "Si deseas probar sin LLM, utiliza la bandera --skip-llm."
        )
        return EXIT_CONFIGURATION_ERROR

    logger.info("--------------------------------------------------")
    logger.info("Fase 3: Evaluando oportunidades con Gemini Flash...")
    logger.info("--------------------------------------------------")

    history = load_history()
    cooldown_days = (
        max(0, args.cooldown_days)
        if args.cooldown_days is not None
        else pipeline_config.history_days_lookback
    )
    history_lookback_days = cooldown_days
    recent_topics = get_recent_topics(history, days=history_lookback_days)
    recent_trigger_titles = get_recent_trigger_titles(history, days=history_lookback_days)
    recent_trigger_urls = get_recent_trigger_urls(history, days=history_lookback_days)

    logger.info(
        "Historial cargado: %d registros previos (%d temas y %d noticias detonantes en los últimos %d días).",
        len(history),
        len(recent_topics),
        len(recent_trigger_urls),
        history_lookback_days,
    )

    # Filtrado determinista de artículos para evitar repetir noticias detonantes
    filtered_articles = filter_articles_by_history(
        articles=articles,
        history=history,
        days=cooldown_days,
    )
    if len(filtered_articles) < len(articles):
        logger.info(
            "Filtro de novedades: %d de %d artículos excluidos por coincidir con noticias de los últimos %d días (%d artículos a evaluar).",
            len(articles) - len(filtered_articles),
            len(articles),
            cooldown_days,
            len(filtered_articles),
        )

    try:
        radar_result = evaluate_opportunities(
            articles=filtered_articles,
            recent_history_topics=recent_topics,
            recent_trigger_titles=recent_trigger_titles,
            exclude_trigger_urls=recent_trigger_urls,
            model_name=args.model,
            min_virality=pipeline_config.min_virality_score,
            min_feasibility=pipeline_config.min_feasibility_score,
            max_opportunities=pipeline_config.max_opportunities_to_notify,
            lookback_hours=lookback_hours,
            history_days=history_lookback_days,
            verify_sources=pipeline_config.verify_source_urls,
            require_verified_source=pipeline_config.require_verified_source,
            source_verification_timeout_seconds=pipeline_config.source_verification_timeout_seconds,
        )
    except Exception as e:
        logger.exception("Error durante la evaluación de oportunidades con Gemini: %s", e)
        return EXIT_EVALUATION_ERROR

    opportunities = radar_result.top_opportunities
    rejected_opportunities = radar_result.rejected_opportunities
    pending_deliveries = get_entries_pending_delivery(history)
    logger.info(
        "Evaluación finalizada: %d oportunidades calificadas y %d descartadas con motivo.",
        len(opportunities),
        len(rejected_opportunities),
    )

    # Registrar los nuevos candidatos antes de cualquier envío. Esto evita que un
    # proceso interrumpido tras Telegram pierda el estado de entrega.
    new_entries = []
    for opp in opportunities:
        new_id = generate_next_id(history)
        entry = HistoryEntry.from_opportunity(
            opp,
            entry_id=new_id,
            delivery_status="skipped" if args.skip_telegram else "pending",
        )
        history.append(entry)
        new_entries.append(entry)

        logger.info("\n🚀 [%s] %s (Viralidad: %d/10 | Viabilidad: %d/10)", new_id, opp.headline, opp.virality_score, opp.technical_feasibility_score)
        logger.info("   📂 Categoría: %s", opp.category)
        logger.info("   🎯 Ángulo: %s", opp.contrarian_or_curious_angle)
        logger.info("   📊 Entregable sugerido: %s", opp.suggested_deliverable)
        if opp.trigger_article_title:
            logger.info("   📰 Noticia detonante: %s (%s)", opp.trigger_article_title, opp.trigger_article_url or "Sin URL")
        logger.info("   🛠️ Plan rápido: %s", opp.fast_execution_strategy)
        for ds in opp.data_sources:
            logger.info("      • Fuente: %s (%s, Fricción: %s)", ds.name, ds.type, ds.friction_level)

    rejected_entries = []
    for rejected in rejected_opportunities:
        new_id = generate_next_id(history)
        entry = HistoryEntry.from_opportunity(
            rejected.opportunity,
            entry_id=new_id,
            delivery_status="skipped",
            evaluation_status="rejected",
            rejection_reason=rejected.reason,
        )
        history.append(entry)
        rejected_entries.append(entry)
        logger.info("↳ [%s] Descartada: %s (%s)", new_id, entry.topic, rejected.reason)

    if not opportunities:
        logger.info("No se detectaron oportunidades nuevas que superaran los umbrales hoy.")

    if args.dry_run:
        logger.info("[DRY-RUN] Historial no modificado.")
    else:
        try:
            save_history(history)
        except Exception as exc:
            logger.exception("No se pudo guardar el historial de oportunidades: %s", exc)
            return EXIT_EVALUATION_ERROR
        logger.info(
            "\nHistorial actualizado exitosamente en data/history.json con %d oportunidades aceptadas y %d descartadas.",
            len(opportunities),
            len(rejected_entries),
        )

    # Fase 4: despacho de candidatos nuevos y reintentos explícitamente pendientes.
    # Los registros históricos sin estado de entrega quedan como ``untracked`` y no
    # se reenvían durante la migración.
    entries_to_dispatch = pending_deliveries + new_entries
    if args.skip_telegram:
        logger.info("Bandera --skip-telegram activa: Omitiendo despacho a Telegram.")
    else:
        logger.info("--------------------------------------------------")
        logger.info("Fase 4: Despachando alertas a Telegram%s...", " (DRY-RUN)" if args.dry_run else "")
        logger.info("--------------------------------------------------")
        dispatch_results = send_batch_alerts(
            opportunities=entries_to_dispatch,
            total_articles=len(articles),
            dry_run=args.dry_run,
        )
        if dispatch_results.get("skipped"):
            logger.warning("Despacho a Telegram omitido por credenciales faltantes.")
        else:
            logger.info(
                "Fase 4 finalizada: %d alertas enviadas (Fallidas: %d, Briefing enviado: %s).",
                dispatch_results.get("sent", 0),
                dispatch_results.get("failed", 0),
                dispatch_results.get("briefing_sent", False),
            )

        # Solo actualizamos el historial si cada resultado individual puede
        # asociarse inequívocamente a su candidato. Así, una respuesta incompleta
        # del notificador mantiene los candidatos en estado pendiente y evita
        # registrarlos como entregados por error.
        item_results = dispatch_results.get("item_results", [])
        if not args.dry_run and not dispatch_results.get("skipped"):
            if len(item_results) != len(entries_to_dispatch):
                logger.error(
                    "El notificador devolvió %d resultados para %d alertas; se conserva el estado pendiente.",
                    len(item_results),
                    len(entries_to_dispatch),
                )
                return EXIT_NOTIFICATION_ERROR
            for entry, delivered in zip(entries_to_dispatch, item_results):
                entry.record_delivery_attempt(bool(delivered))
            try:
                save_history(history)
            except Exception as exc:
                logger.exception("No se pudo persistir el resultado del despacho: %s", exc)
                return EXIT_EVALUATION_ERROR

        if not _dispatch_succeeded(dispatch_results):
            logger.error("El despacho a Telegram no se completó correctamente.")
            return EXIT_NOTIFICATION_ERROR

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
