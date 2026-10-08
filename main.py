"""Data Newsjacking Radar (DNR) - Pipeline Entrypoint."""

import argparse
from collections import Counter
import logging
import os
import sys
from dotenv import load_dotenv

from src.analysis import evaluate_opportunities
from src.ingestion import gather_all_sources
from src.notifiers import send_batch_alerts
from src.storage import (
    HistoryEntry,
    generate_next_id,
    get_recent_topics,
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


def main() -> None:
    """Ejecuta el pipeline principal de Data Newsjacking Radar."""
    parser = argparse.ArgumentParser(description="Data Newsjacking Radar (DNR)")
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

    logger.info("==================================================")
    logger.info("Iniciando Data Newsjacking Radar (DNR)")
    logger.info("==================================================")

    # Fase 1: Ingesta de fuentes (Prensa RSS + Reddit) o carga desde cache
    if args.use_cache:
        logger.info("Modo desarrollo: Intentando cargar artículos desde cache local...")
        articles = load_articles_cache()
        if not articles:
            logger.info("Cache vacío o no encontrado. Ejecutando recolección en vivo...")
            articles = gather_all_sources()
            save_articles_cache(articles)
    else:
        articles = gather_all_sources()
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
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.error(
            "GEMINI_API_KEY no encontrada en variables de entorno o archivo .env. "
            "Para ejecutar la evaluación de oportunidades, configura tu API key en .env. "
            "Si deseas probar sin LLM, utiliza la bandera --skip-llm."
        )
        sys.exit(1)

    logger.info("--------------------------------------------------")
    logger.info("Fase 3: Evaluando oportunidades con Gemini Flash...")
    logger.info("--------------------------------------------------")

    history = load_history()
    recent_topics = get_recent_topics(history, days=7)
    logger.info(
        "Historial cargado: %d registros previos (%d temas analizados en los últimos 7 días).",
        len(history),
        len(recent_topics),
    )

    try:
        radar_result = evaluate_opportunities(
            articles=articles,
            recent_history_topics=recent_topics,
        )
    except Exception as e:
        logger.error("Error durante la evaluación de oportunidades con Gemini: %s", e)
        return

    opportunities = radar_result.top_opportunities
    logger.info(
        "Evaluación finalizada: %d oportunidades calificadas sobre el umbral.",
        len(opportunities),
    )

    if not opportunities:
        logger.info("No se detectaron oportunidades que superaran los umbrales de viabilidad y viralidad hoy.")
        if not args.skip_telegram:
            logger.info("Despachando notificación de estado a Telegram (0 oportunidades)...")
            send_batch_alerts(
                opportunities=[],
                total_articles=len(articles),
                dry_run=args.dry_run,
            )
        return

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

    save_history(history)
    logger.info("\nHistorial actualizado exitosamente en data/history.json con %d oportunidades nuevas.", len(opportunities))

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


if __name__ == "__main__":
    main()
