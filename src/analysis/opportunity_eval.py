"""Evaluador de oportunidades mediante Gemini API y Pydantic."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class DataSource(BaseModel):
    name: str
    type: Literal[
        "API Pública",
        "Tabla Wikipedia",
        "Portal Abierto",
        "Scraping HTML",
        "Dataset Descargable",
    ]
    potential_url_or_query: str
    friction_level: Literal[
        "Baja (Horas)",
        "Media (1-2 días)",
        "Alta (Requiere peticiones de transparencia)",
    ]


class Opportunity(BaseModel):
    headline: str
    category: Literal[
        "Economía & Finanzas",
        "Política & Estado",
        "Deportes",
        "Sociedad & Tendencias",
    ]
    why_is_trending: str
    contrarian_or_curious_angle: str = Field(
        description="El gancho cognitivo: qué mito se desmiente o qué duda resuelve"
    )
    suggested_deliverable: Literal[
        "Gráfico Estático de Alto Impacto",
        "App Interactiva (Streamlit)",
        "Análisis Predictivo/Optimización",
    ]
    data_sources: List[DataSource]
    virality_score: int = Field(ge=1, le=10)
    technical_feasibility_score: int = Field(ge=1, le=10)
    fast_execution_strategy: str = Field(
        description="Plan de acción concreto en 3 pasos para construirlo en menos de 4 horas"
    )


class RadarResponse(BaseModel):
    evaluated_topics_count: int
    top_opportunities: List[Opportunity]


def evaluate_opportunities(
    news_items: List[Dict[str, Any]],
    recent_history: Optional[List[Dict[str, Any]]] = None,
) -> RadarResponse:
    """Evaluate candidate news items using Gemini Flash structured output."""
    raise NotImplementedError("Will be implemented in Step 3")
