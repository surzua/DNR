"""Data models for the ingestion layer."""

from datetime import datetime, timezone
import html
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

HTML_TAG_RE = re.compile(r"<[^>]+>")


class NewsArticle(BaseModel):
    """Representa un artículo o publicación ingerida desde RSS o redes sociales."""

    title: str = Field(description="Título de la noticia o hilo")
    link: str = Field(description="Enlace permanente a la publicación")
    summary: str = Field(default="", description="Resumen o contenido inicial")
    published_at: datetime = Field(description="Fecha y hora de publicación en UTC")
    source: str = Field(description="Nombre de la fuente (e.g. La Tercera, BioBioChile, Reddit)")
    category: Optional[str] = Field(default=None, description="Categoría o sección de la noticia")
    score: Optional[int] = Field(default=None, description="Métrica de interacción (e.g. upvotes en Reddit)")
    comments_count: Optional[int] = Field(default=None, description="Número de comentarios si aplica")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def clean_text(cls, value: str) -> str:
        """Limpia tags HTML, entidades y espacios redundantes."""
        if not isinstance(value, str):
            return ""
        # Decodificar entidades HTML (&amp;, &#8220;, etc.)
        unescaped = html.unescape(value)
        # Eliminar cualquier tag HTML (<p>, <img>, <a>, etc.)
        stripped = HTML_TAG_RE.sub(" ", unescaped)
        # Normalizar espacios en blanco
        return " ".join(stripped.strip().split())

    @field_validator("published_at", mode="before")
    @classmethod
    def ensure_utc(cls, value: datetime | str) -> datetime:
        """Asegura que la fecha tenga zona horaria UTC."""
        if isinstance(value, str):
            from dateutil import parser
            dt = parser.parse(value)
        else:
            dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
