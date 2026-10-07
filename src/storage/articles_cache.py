"""Módulo de persistencia local y cache para artículos de noticias ingeridos."""

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import List
from src.ingestion.models import NewsArticle

logger = logging.getLogger("dnr.articles_cache")

DEFAULT_CACHE_PATH = Path("data/latest_articles.json")


def save_articles_cache(
    articles: List[NewsArticle],
    filepath: Path = DEFAULT_CACHE_PATH,
) -> Path:
    """Guarda un snapshot de los artículos ingeridos en un archivo JSON local de forma atómica."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    serialized = [item.model_dump(mode="json") for item in articles]
    temp_file = tempfile.NamedTemporaryFile(
        "w",
        dir=filepath.parent,
        delete=False,
        encoding="utf-8",
        suffix=".tmp",
    )
    temp_path = Path(temp_file.name)
    try:
        with temp_file as f:
            json.dump(serialized, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, filepath)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        logger.error("Fallo durante guardado atómico de cache en %s: %s", filepath, exc)
        raise exc

    logger.info("Snapshot local guardado: %d artículos en %s", len(articles), filepath)
    return filepath


def load_articles_cache(
    filepath: Path = DEFAULT_CACHE_PATH,
) -> List[NewsArticle]:
    """Carga artículos desde el snapshot JSON local para desarrollo o reanálisis."""
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning("Archivo de cache no encontrado: %s", filepath)
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Contenido de cache inválido en %s", filepath)
                return []
            articles = [NewsArticle.model_validate(item) for item in data]
            logger.info("Cargados %d artículos desde cache: %s", len(articles), filepath)
            return articles
    except Exception as exc:
        logger.warning("Error al leer cache desde %s: %s", filepath, exc)
        return []
