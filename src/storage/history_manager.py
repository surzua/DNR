"""Manejo de lectura/escritura y deduplicación de historial."""

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("dnr.history_manager")

HISTORY_FILE_PATH = Path("data/history.json")


class HistoryEntry(BaseModel):
    """Representa un registro histórico de una oportunidad analizada."""

    id: str = Field(description="Identificador único (ej. 2026-10-06-001)")
    timestamp: datetime = Field(description="Fecha y hora de registro en UTC")
    topic: str = Field(description="Titular o tema analizado")
    category: str = Field(description="Categoría temática")
    viral_hook_type: str = Field(description="Tipo de gancho viral")
    analytical_angle: str = Field(description="Ángulo analítico o hipótesis")
    data_sources: List[Dict[str, Any]] = Field(default_factory=list, description="Fuentes de datos sugeridas")
    feasibility_score: int = Field(description="Puntaje de factibilidad técnica (1-10)")
    virality_score: int = Field(description="Puntaje de potencial viral (1-10)")
    recommended_deliverable: str = Field(description="Formato de entrega sugerido")
    fast_execution_strategy: Optional[str] = Field(default=None, description="Estrategia rápida de ejecución")
    status: str = Field(default="candidate", description="Estado de la oportunidad")

    @classmethod
    def from_opportunity(
        cls,
        opportunity: Any,
        entry_id: str,
        timestamp: Optional[datetime] = None,
        status: str = "candidate",
    ) -> "HistoryEntry":
        """Convierte un objeto Opportunity a HistoryEntry."""
        ts = timestamp or datetime.now(timezone.utc)
        data_sources = [
            ds.model_dump() if hasattr(ds, "model_dump") else dict(ds)
            for ds in getattr(opportunity, "data_sources", [])
        ]
        return cls(
            id=entry_id,
            timestamp=ts,
            topic=getattr(opportunity, "headline", ""),
            category=getattr(opportunity, "category", ""),
            viral_hook_type="Contrarian / Curious Hook",
            analytical_angle=getattr(opportunity, "contrarian_or_curious_angle", ""),
            data_sources=data_sources,
            feasibility_score=getattr(opportunity, "technical_feasibility_score", 0),
            virality_score=getattr(opportunity, "virality_score", 0),
            recommended_deliverable=getattr(opportunity, "suggested_deliverable", ""),
            fast_execution_strategy=getattr(opportunity, "fast_execution_strategy", None),
            status=status,
        )


def load_history(filepath: Path = HISTORY_FILE_PATH) -> List[HistoryEntry]:
    """Carga y valida el historial de oportunidades analizadas."""
    if not filepath.exists():
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.warning("El archivo de historial no contiene una lista válida.")
                return []
            return [HistoryEntry.model_validate(item) for item in data]
    except Exception as e:
        logger.warning("Error al cargar historial desde %s: %s", filepath, e)
        return []


def save_history(history: List[HistoryEntry], filepath: Path = HISTORY_FILE_PATH) -> None:
    """Guarda el historial serializado como JSON formateado."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    serialized = [item.model_dump(mode="json") for item in history]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)


def get_recent_topics(
    history: Optional[List[HistoryEntry]] = None,
    days: int = 7,
    now: Optional[datetime] = None,
    filepath: Path = HISTORY_FILE_PATH,
) -> List[str]:
    """Obtiene los temas analizados en los últimos N días para deduplicación semántica."""
    items = history if history is not None else load_history(filepath)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    return [
        item.topic
        for item in items
        if item.timestamp.astimezone(timezone.utc) >= cutoff
    ]


def generate_next_id(
    history: List[HistoryEntry],
    target_date: Optional[datetime] = None,
) -> str:
    """Genera el próximo ID secuencial para una fecha dada (formato YYYY-MM-DD-00X)."""
    date_str = (target_date or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    prefix = f"{date_str}-"
    same_day_ids = [
        int(item.id.replace(prefix, ""))
        for item in history
        if item.id.startswith(prefix) and item.id.replace(prefix, "").isdigit()
    ]
    next_seq = max(same_day_ids, default=0) + 1
    return f"{prefix}{next_seq:03d}"
