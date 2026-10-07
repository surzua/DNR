"""Data Newsjacking Radar (DNR) - Pipeline Entrypoint."""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("dnr.main")


def main() -> None:
    """Ejecuta el pipeline principal de Data Newsjacking Radar."""
    logger.info("Iniciando Data Newsjacking Radar (DNR)...")
    logger.info("Pipeline inicializado con éxito. Listo para ejecución de fases.")


if __name__ == "__main__":
    main()
