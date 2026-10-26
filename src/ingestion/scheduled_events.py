"""Eventos previsibles configurados manualmente como señales trazables."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.ingestion.models import NewsArticle

logger = logging.getLogger("dnr.scheduled_events")


def fetch_scheduled_events(config_path: str = "config/sources.yaml") -> List[NewsArticle]:
    """Convierte eventos con fecha y fuente configuradas en señales del radar."""
    try:
        raw_config: Dict[str, Any] = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Eventos programados omitidos: %s", exc)
        return []
    now = datetime.now(timezone.utc)
    events: List[NewsArticle] = []
    for item in raw_config.get("scheduled_events", []):
        if not isinstance(item, dict) or not item.get("title") or not item.get("source_url") or not item.get("date"):
            logger.warning("Evento programado inválido u omitido: %r", item)
            continue
        try:
            event_date = datetime.fromisoformat(str(item["date"]).replace("Z", "+00:00"))
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            event_date = event_date.astimezone(timezone.utc)
        except ValueError:
            logger.warning("Evento programado con fecha inválida: %r", item.get("date"))
            continue
        events.append(NewsArticle(
            title=str(item["title"]), link=str(item["source_url"]),
            summary=str(item.get("summary", "Evento futuro configurado manualmente.")),
            published_at=event_date, first_detected_at=now,
            source=str(item.get("source", "Calendario oficial")), category=item.get("category"),
            signal_type="scheduled_event",
            signal_limitations="Evento previsto: confirmar fecha, reglas y vigencia con la fuente enlazada.",
        ))
    return events
