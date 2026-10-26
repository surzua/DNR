"""Manejo de lectura/escritura y deduplicación de historial."""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Dict, List, Literal, Optional, Set
import unicodedata
from urllib.parse import urlparse
from pydantic import BaseModel, Field

logger = logging.getLogger("dnr.history_manager")

HISTORY_FILE_PATH = Path("data/history.json")


class PublicationMetrics(BaseModel):
    """Mediciones acumuladas y manuales de una herramienta publicada."""

    visits: int = Field(default=0, ge=0, description="Visitas o sesiones observadas")
    task_completions: int = Field(default=0, ge=0, description="Personas que llegaron al resultado útil")
    share_clicks: int = Field(default=0, ge=0, description="Clics para compartir o copiar enlace")
    corrections: int = Field(default=0, ge=0, description="Correcciones o incidencias de calidad")
    hours_invested: float = Field(default=0.0, ge=0, description="Horas reales invertidas")
    measured_at: Optional[datetime] = Field(
        default=None,
        description="Momento UTC de la última actualización de métricas",
    )


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
    trigger_article_title: Optional[str] = Field(default=None, description="Titular de la noticia detonante")
    trigger_article_url: Optional[str] = Field(default=None, description="URL de la noticia detonante")
    status: str = Field(default="candidate", description="Estado de la oportunidad")
    evaluation_status: str = Field(
        default="accepted",
        description="Resultado de la evaluación que creó este registro",
    )
    delivery_status: str = Field(
        default="untracked",
        description="Estado del envío: untracked, pending, delivered, failed o skipped",
    )
    delivery_attempts: int = Field(default=0, ge=0, description="Intentos de entrega registrados")
    last_delivery_attempt_at: Optional[datetime] = Field(
        default=None,
        description="Momento UTC del último intento de entrega",
    )
    delivered_at: Optional[datetime] = Field(
        default=None,
        description="Momento UTC del último envío confirmado",
    )
    publication_status: Literal["unpublished", "selected", "published", "archived"] = Field(
        default="unpublished",
        description="Estado de publicación: unpublished, selected, published o archived",
    )
    selected_at: Optional[datetime] = Field(default=None, description="Momento UTC de selección")
    published_at: Optional[datetime] = Field(default=None, description="Momento UTC de publicación")
    archived_at: Optional[datetime] = Field(default=None, description="Momento UTC de archivo")
    product_url: Optional[str] = Field(default=None, description="URL pública del producto publicado")
    publication_notes: Optional[str] = Field(default=None, description="Notas operativas de publicación")
    metrics: PublicationMetrics = Field(default_factory=PublicationMetrics)
    audience: Optional[str] = Field(default=None, description="Audiencia objetivo del producto")
    user_need: Optional[str] = Field(default=None, description="Necesidad que resuelve")
    user_action: Optional[str] = Field(default=None, description="Acción que podrá completar la audiencia")
    product_type: Optional[str] = Field(default=None, description="Tipo de producto propuesto")
    product_inputs: Optional[str] = Field(default=None, description="Entradas mínimas del producto")
    product_output: Optional[str] = Field(default=None, description="Resultado para la audiencia")
    share_reason: Optional[str] = Field(default=None, description="Motivo para compartir el resultado")
    evidence_status: str = Field(
        default="Propuesta (no verificada)",
        description="Nivel de comprobación de fuentes o reglas",
    )
    validity_note: Optional[str] = Field(default=None, description="Nota o condición de vigencia")
    known_facts: List[str] = Field(
        default_factory=list,
        description="Hechos conocidos del detonante, separados de las hipótesis",
    )
    hypotheses_to_test: List[str] = Field(
        default_factory=list,
        description="Hipótesis pendientes de comprobar durante la producción",
    )
    verification_plan: List[str] = Field(
        default_factory=list,
        description="Controles requeridos antes de publicar",
    )
    distribution_channel: Optional[str] = Field(
        default=None,
        description="Canal inicial de distribución propuesto",
    )
    existing_alternatives: Optional[str] = Field(
        default=None,
        description="Alternativas existentes y diferenciación propuesta",
    )
    selection_scores: Dict[str, int] = Field(
        default_factory=dict,
        description="Dimensiones de la rúbrica usada al seleccionar la oportunidad",
    )
    priority_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=5,
        description="Prioridad ponderada de la oportunidad, de 0 a 5",
    )

    @classmethod
    def from_opportunity(
        cls,
        opportunity: Any,
        entry_id: str,
        timestamp: Optional[datetime] = None,
        status: str = "candidate",
        delivery_status: str = "pending",
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
            trigger_article_title=getattr(opportunity, "trigger_article_title", None),
            trigger_article_url=getattr(opportunity, "trigger_article_url", None),
            status=status,
            evaluation_status="accepted",
            delivery_status=delivery_status,
            publication_status="unpublished",
            audience=getattr(opportunity, "audience", None),
            user_need=getattr(opportunity, "user_need", None),
            user_action=getattr(opportunity, "user_action", None),
            product_type=getattr(opportunity, "product_type", None),
            product_inputs=getattr(opportunity, "product_inputs", None),
            product_output=getattr(opportunity, "product_output", None),
            share_reason=getattr(opportunity, "share_reason", None),
            evidence_status=getattr(opportunity, "evidence_status", "Propuesta (no verificada)"),
            validity_note=getattr(opportunity, "validity_note", None),
            known_facts=getattr(opportunity, "known_facts", []),
            hypotheses_to_test=getattr(opportunity, "hypotheses_to_test", []),
            verification_plan=getattr(opportunity, "verification_plan", []),
            distribution_channel=getattr(opportunity, "distribution_channel", None),
            existing_alternatives=getattr(opportunity, "existing_alternatives", None),
            selection_scores=(
                getattr(opportunity, "assessment").model_dump()
                if hasattr(getattr(opportunity, "assessment", None), "model_dump")
                else {}
            ),
            priority_score=(
                getattr(opportunity, "assessment").priority_score()
                if callable(getattr(getattr(opportunity, "assessment", None), "priority_score", None))
                else None
            ),
        )

    def record_delivery_attempt(
        self,
        delivered: bool,
        attempted_at: Optional[datetime] = None,
    ) -> None:
        """Actualiza el resultado de un intento de envío confirmado por Telegram."""
        timestamp = attempted_at or datetime.now(timezone.utc)
        self.delivery_attempts += 1
        self.last_delivery_attempt_at = timestamp
        if delivered:
            self.delivery_status = "delivered"
            self.delivered_at = timestamp
        else:
            self.delivery_status = "failed"

    def mark_selected(self, selected_at: Optional[datetime] = None) -> None:
        """Marca la oportunidad como elegida para producción."""
        self.publication_status = "selected"
        self.selected_at = self.selected_at or selected_at or datetime.now(timezone.utc)

    def mark_published(
        self,
        product_url: str,
        notes: Optional[str] = None,
        published_at: Optional[datetime] = None,
    ) -> None:
        """Registra una publicación y la URL pública de la herramienta."""
        parsed_url = urlparse(product_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("La URL del producto debe ser HTTP(S) y tener un host válido.")

        timestamp = published_at or datetime.now(timezone.utc)
        if self.selected_at is None:
            self.selected_at = timestamp
        self.publication_status = "published"
        self.published_at = timestamp
        self.archived_at = None
        self.product_url = product_url.strip()
        if notes is not None:
            self.publication_notes = notes.strip() or None

    def mark_archived(
        self,
        notes: Optional[str] = None,
        archived_at: Optional[datetime] = None,
    ) -> None:
        """Archiva un producto u oportunidad que ya no se mantendrá vigente."""
        self.publication_status = "archived"
        self.archived_at = archived_at or datetime.now(timezone.utc)
        if notes is not None:
            self.publication_notes = notes.strip() or None

    def update_metrics(
        self,
        *,
        visits: Optional[int] = None,
        task_completions: Optional[int] = None,
        share_clicks: Optional[int] = None,
        corrections: Optional[int] = None,
        hours_invested: Optional[float] = None,
        measured_at: Optional[datetime] = None,
    ) -> None:
        """Guarda el último total observado de métricas de publicación."""
        values = {
            "visits": visits,
            "task_completions": task_completions,
            "share_clicks": share_clicks,
            "corrections": corrections,
            "hours_invested": hours_invested,
        }
        for name, value in values.items():
            if value is not None:
                if value < 0:
                    raise ValueError(f"{name} no puede ser negativo.")
                setattr(self.metrics, name, value)
        self.metrics.measured_at = measured_at or datetime.now(timezone.utc)


def find_history_entry(history: List[HistoryEntry], entry_id: str) -> Optional[HistoryEntry]:
    """Busca una oportunidad por su identificador estable."""
    return next((entry for entry in history if entry.id == entry_id), None)


def get_publication_report(
    history: List[HistoryEntry],
    days: int = 7,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Resume publicaciones y métricas acumuladas dentro de una ventana temporal."""
    if days < 1:
        raise ValueError("days debe ser mayor o igual a 1.")

    reference_time = now or datetime.now(timezone.utc)
    cutoff = reference_time - timedelta(days=days)
    published = [
        entry
        for entry in history
        if entry.publication_status == "published"
        and entry.published_at is not None
        and entry.published_at.astimezone(timezone.utc) >= cutoff
    ]
    selected = [
        entry
        for entry in history
        if entry.publication_status == "selected"
        and entry.selected_at is not None
        and entry.selected_at.astimezone(timezone.utc) >= cutoff
    ]
    archived = [
        entry
        for entry in history
        if entry.publication_status == "archived"
        and entry.archived_at is not None
        and entry.archived_at.astimezone(timezone.utc) >= cutoff
    ]
    return {
        "days": days,
        "published": len(published),
        "selected": len(selected),
        "archived": len(archived),
        "visits": sum(entry.metrics.visits for entry in published),
        "task_completions": sum(entry.metrics.task_completions for entry in published),
        "share_clicks": sum(entry.metrics.share_clicks for entry in published),
        "corrections": sum(entry.metrics.corrections for entry in published),
        "hours_invested": sum(entry.metrics.hours_invested for entry in published),
        "published_entries": published,
    }


def get_entries_pending_delivery(history: List[HistoryEntry]) -> List[HistoryEntry]:
    """Retorna alertas nuevas o fallidas que se pueden reintentar.

    Los registros históricos previos al seguimiento quedan como ``untracked``;
    así la migración no reenvía retrospectivamente alertas ya vistas.
    """
    return [entry for entry in history if entry.delivery_status in {"pending", "failed"}]


def load_history(filepath: Path = HISTORY_FILE_PATH) -> List[HistoryEntry]:
    """Carga y valida el historial de oportunidades analizadas.

    Si el archivo está dañado, preserva una copia de seguridad (.corrupt.bak)
    antes de retornar lista vacía, previniendo pérdida silenciosa de datos.
    """
    filepath = Path(filepath)
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
        # Resguardo de seguridad: preservar archivo corrupto para auditoría/recuperación
        try:
            backup_path = filepath.with_suffix(".corrupt.bak")
            shutil.copyfile(filepath, backup_path)
            logger.error("Copia de seguridad del historial dañado guardada en: %s", backup_path)
        except Exception as copy_err:
            logger.warning("No se pudo crear backup del archivo dañado: %s", copy_err)
        return []


def save_history(history: List[HistoryEntry], filepath: Path = HISTORY_FILE_PATH) -> None:
    """Guarda el historial serializado como JSON formateado de forma atómica.

    Utiliza un archivo temporal y reemplazo atómico para evitar corrupción por abortos
    o cortes de proceso en ejecuciones desatendidas.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    serialized = [item.model_dump(mode="json") for item in history]

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
        logger.error("Fallo durante guardado atómico del historial en %s: %s", filepath, exc)
        raise exc


def get_recent_topics(
    history: Optional[List[HistoryEntry]] = None,
    days: int = 2,
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


def normalize_url_for_dedup(url: Optional[str]) -> str:
    """Normaliza una URL para comparación determinista y deduplicación.

    Elimina protocolo (http/https), prefijo 'www.', parámetros de consulta,
    fragmentos y barras finales para asociar variantes del mismo enlace.
    """
    if not url or not isinstance(url, str):
        return ""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/").lower()
    return f"{netloc}{path}"


def normalize_title_for_dedup(title: Optional[str]) -> str:
    """Normaliza un titular eliminando tildes, caracteres especiales y normalizando espacios."""
    if not title or not isinstance(title, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", title)
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", " ", without_accents.lower()).strip()


def get_recent_trigger_urls(
    history: Optional[List[HistoryEntry]] = None,
    days: int = 2,
    now: Optional[datetime] = None,
    filepath: Path = HISTORY_FILE_PATH,
) -> Set[str]:
    """Obtiene el conjunto de URLs detonantes normalizadas en los últimos N días."""
    items = history if history is not None else load_history(filepath)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    urls: Set[str] = set()
    for item in items:
        if item.timestamp.astimezone(timezone.utc) >= cutoff and item.trigger_article_url:
            norm = normalize_url_for_dedup(item.trigger_article_url)
            if norm:
                urls.add(norm)
    return urls


def get_recent_trigger_titles(
    history: Optional[List[HistoryEntry]] = None,
    days: int = 2,
    now: Optional[datetime] = None,
    filepath: Path = HISTORY_FILE_PATH,
) -> List[str]:
    """Obtiene los titulares originales de noticias detonantes de los últimos N días."""
    items = history if history is not None else load_history(filepath)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    titles: List[str] = []
    seen: Set[str] = set()
    for item in items:
        if item.timestamp.astimezone(timezone.utc) >= cutoff and item.trigger_article_title:
            cleaned = item.trigger_article_title.strip()
            norm = normalize_title_for_dedup(cleaned)
            if norm and norm not in seen:
                seen.add(norm)
                titles.append(cleaned)
    return titles


def filter_articles_by_history(
    articles: List[Any],
    history: Optional[List[HistoryEntry]] = None,
    days: int = 2,
    now: Optional[datetime] = None,
    filepath: Path = HISTORY_FILE_PATH,
) -> List[Any]:
    """Filtra y excluye artículos que ya hayan sido usados como noticia detonante en los últimos N días.

    Compara tanto URL normalizada como titular normalizado con el historial.
    """
    if days <= 0:
        return articles

    items = history if history is not None else load_history(filepath)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)

    recent_urls: Set[str] = set()
    recent_titles: Set[str] = set()

    for item in items:
        if item.timestamp.astimezone(timezone.utc) >= cutoff:
            if item.trigger_article_url:
                norm_u = normalize_url_for_dedup(item.trigger_article_url)
                if norm_u:
                    recent_urls.add(norm_u)
            if item.trigger_article_title:
                norm_t = normalize_title_for_dedup(item.trigger_article_title)
                if norm_t:
                    recent_titles.add(norm_t)

    if not recent_urls and not recent_titles:
        return articles

    kept: List[Any] = []
    for art in articles:
        link = getattr(art, "link", "") or (art.get("link", "") if isinstance(art, dict) else "")
        title = getattr(art, "title", "") or (art.get("title", "") if isinstance(art, dict) else "")

        norm_link = normalize_url_for_dedup(link)
        norm_title = normalize_title_for_dedup(title)

        if norm_link and norm_link in recent_urls:
            continue
        if norm_title and norm_title in recent_titles:
            continue

        kept.append(art)

    return kept


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
