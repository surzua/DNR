"""Data Newsjacking Radar (DNR) - Pipeline Entrypoint."""

import argparse
from collections import Counter
import logging
import sys

from src.ingestion import gather_all_sources
from src.storage import load_articles_cache, save_articles_cache

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

    logger.info("Pipeline listo para Fase de Evaluación con LLM (Paso 3).")


if __name__ == "__main__":
    main()
