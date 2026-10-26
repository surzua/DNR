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
    filter_articles_by_history,
    generate_next_id,
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
    args = parser.parse_args()

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
        )
    except Exception as e:
        logger.exception("Error durante la evaluación de oportunidades con Gemini: %s", e)
        return EXIT_EVALUATION_ERROR

    opportunities = radar_result.top_opportunities
    logger.info(
        "Evaluación finalizada: %d oportunidades calificadas sobre el umbral.",
        len(opportunities),
    )

    if not opportunities:
        logger.info("No se detectaron oportunidades que superaran los umbrales de viabilidad y viralidad hoy.")
        if not args.skip_telegram:
            logger.info("Despachando notificación de estado a Telegram (0 oportunidades)...")
            dispatch_results = send_batch_alerts(
                opportunities=[],
                total_articles=len(articles),
                dry_run=args.dry_run,
            )
            if not _dispatch_succeeded(dispatch_results):
                logger.error("No se pudo entregar el briefing de estado a Telegram.")
                return EXIT_NOTIFICATION_ERROR
        return EXIT_SUCCESS

    # Guardado de oportunidades en historial
    for opp in opportunities:
        new_id = generate_next_id(history)
        entry = HistoryEntry.from_opportunity(opp, entry_id=new_id)
        history.append(entry)

        logger.info("\n🚀 [%s] %s (Viralidad: %d/10 | Viabilidad: %d/10)", new_id, opp.headline, opp.virality_score, opp.technical_feasibility_score)
        logger.info("   📂 Categoría: %s", opp.category)
        logger.info("   🎯 Ángulo: %s", opp.contrarian_or_curious_angle)
        logger.info("   📊 Entregable sugerido: %s", opp.suggested_deliverable)
        if opp.trigger_article_title:
            logger.info("   📰 Noticia detonante: %s (%s)", opp.trigger_article_title, opp.trigger_article_url or "Sin URL")
        logger.info("   🛠️ Plan rápido: %s", opp.fast_execution_strategy)
        for ds in opp.data_sources:
            logger.info("      • Fuente: %s (%s, Fricción: %s)", ds.name, ds.type, ds.friction_level)

    if args.dry_run:
        logger.info("[DRY-RUN] Historial no modificado.")
    else:
        try:
            save_history(history)
        except Exception as exc:
            logger.exception("No se pudo guardar el historial de oportunidades: %s", exc)
            return EXIT_EVALUATION_ERROR
        logger.info(
            "\nHistorial actualizado exitosamente en data/history.json con %d oportunidades nuevas.",
            len(opportunities),
        )

    # Fase 4: Despacho de alertas a Telegram
    if args.skip_telegram:
        logger.info("Bandera --skip-telegram activa: Omitiendo despacho a Telegram.")
    else:
        logger.info("--------------------------------------------------")
        logger.info("Fase 4: Despachando alertas a Telegram%s...", " (DRY-RUN)" if args.dry_run else "")
        logger.info("--------------------------------------------------")
        dispatch_results = send_batch_alerts(
            opportunities=opportunities,
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
        if not _dispatch_succeeded(dispatch_results):
            logger.error("El despacho a Telegram no se completó correctamente.")
            return EXIT_NOTIFICATION_ERROR

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
