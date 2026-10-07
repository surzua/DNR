"""Data Newsjacking Radar (DNR) - Pipeline Entrypoint."""

from collections import Counter
import logging
import sys

from src.ingestion import gather_all_sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("dnr.main")


def main() -> None:
    """Ejecuta el pipeline principal de Data Newsjacking Radar."""
    logger.info("==================================================")
    logger.info("Iniciando Data Newsjacking Radar (DNR)")
    logger.info("==================================================")

    # Fase 1: Ingesta de fuentes (Prensa RSS + Reddit)
    articles = gather_all_sources()
    logger.info("Fase de Ingesta completada exitosamente: %d artículos recopilados", len(articles))

    # Resumen por fuente
    counts = Counter(a.source for a in articles)
    for source_name, count in counts.most_common():
        logger.info("  • %s: %d artículos", source_name, count)

    logger.info("Pipeline listo para Fase de Evaluación con LLM (Paso 3).")


if __name__ == "__main__":
    main()
