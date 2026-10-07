"""Evaluador de oportunidades mediante Gemini API y Pydantic."""

import json
import logging
import os
from typing import Any, List, Literal, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from src.analysis.prompt_templates import SYSTEM_PROMPT, build_evaluation_prompt

load_dotenv()
logger = logging.getLogger("dnr.opportunity_eval")


class DataSource(BaseModel):
    """Fuente de datos requerida para el desarrollo del análisis."""

    name: str = Field(description="Nombre descriptivo de la fuente o institución")
    type: Literal[
        "API Pública",
        "Tabla Wikipedia",
        "Portal Abierto",
        "Scraping HTML",
        "Dataset Descargable",
    ] = Field(description="Tipo de acceso técnico a los datos")
    potential_url_or_query: str = Field(
        description="URL directa o término de búsqueda exacto para encontrar la data"
    )
    friction_level: Literal[
        "Baja (Horas)",
        "Media (1-2 días)",
        "Alta (Requiere peticiones de transparencia)",
    ] = Field(description="Estimación del tiempo y complejidad para obtener el dataset")


class Opportunity(BaseModel):
    """Oportunidad de proyecto de data journalism o analytics detectada."""

    headline: str = Field(description="Titular sintético y llamativo del proyecto")
    category: Literal[
        "Economía & Finanzas",
        "Política & Estado",
        "Deportes",
        "Sociedad & Tendencias",
    ] = Field(description="Categoría temática principal")
    why_is_trending: str = Field(
        description="Por qué este tema está caliente en la discusión pública hoy"
    )
    contrarian_or_curious_angle: str = Field(
        description="El gancho cognitivo: qué mito se desmiente o qué duda resuelve"
    )
    suggested_deliverable: Literal[
        "Gráfico Estático de Alto Impacto",
        "App Interactiva (Streamlit)",
        "Análisis Predictivo/Optimización",
    ] = Field(description="Formato recomendado para maximizar viralidad y rapidez")
    data_sources: List[DataSource] = Field(
        description="Fuentes de datos públicas necesarias"
    )
    virality_score: int = Field(
        ge=1, le=10, description="Potencial viral y de debate público (1-10)"
    )
    technical_feasibility_score: int = Field(
        ge=1, le=10, description="Viabilidad técnica de construir en < 4 horas (1-10)"
    )
    fast_execution_strategy: str = Field(
        description="Plan de acción concreto en 3 pasos para construirlo en menos de 4 horas"
    )
    trigger_article_title: Optional[str] = Field(
        default=None,
        description="Titular exacto de la noticia o publicación detonante",
    )
    trigger_article_url: Optional[str] = Field(
        default=None,
        description="Enlace web directo a la noticia o publicación detonante",
    )


class RadarResponse(BaseModel):
    """Estructura de respuesta completa del evaluador de radar."""

    evaluated_topics_count: int = Field(
        description="Cantidad aproximada de temas o noticias analizadas"
    )
    top_opportunities: List[Opportunity] = Field(
        default_factory=list,
        description="Oportunidades destacadas que superaron los umbrales de viabilidad",
    )


def filter_and_rank_opportunities(
    opportunities: List[Opportunity],
    min_virality: int = 7,
    min_feasibility: int = 6,
    max_items: int = 3,
) -> List[Opportunity]:
    """Aplica filtros deterministas de umbral y ordena por score combinado descendente."""
    valid = [
        opp
        for opp in opportunities
        if opp.virality_score >= min_virality
        and opp.technical_feasibility_score >= min_feasibility
    ]
    # Ordenar por puntaje total combinado (viralidad + factibilidad técnica) y luego por viralidad
    valid.sort(
        key=lambda o: (o.virality_score + o.technical_feasibility_score, o.virality_score),
        reverse=True,
    )
    return valid[:max_items]


def evaluate_opportunities(
    articles: List[Any],
    recent_history_topics: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    client: Optional[Any] = None,
    min_virality: int = 7,
    min_feasibility: int = 6,
    max_opportunities: int = 3,
) -> RadarResponse:
    """Evalúa candidatos de noticias utilizando Gemini y Structured Outputs Pydantic.

    Args:
        articles: Lista de objetos NewsArticle o diccionarios con noticias.
        recent_history_topics: Lista opcional de temas de los últimos días para deduplicar.
        api_key: Gemini API Key opcional (usa GEMINI_API_KEY del entorno por defecto).
        model_name: Nombre del modelo a usar (por defecto gemini-2.5-flash).
        client: Cliente de Gemini inyectable (útil para pruebas unitarias).
        min_virality: Puntaje mínimo de viralidad requerido (defecto: 7).
        min_feasibility: Puntaje mínimo de factibilidad técnica requerido (defecto: 6).
        max_opportunities: Máximo de oportunidades a retornar (defecto: 3).

    Returns:
        RadarResponse con la cantidad de temas evaluados y las mejores oportunidades filtradas.
    """
    if not articles:
        logger.info("No se proporcionaron artículos para evaluar. Retornando respuesta vacía.")
        return RadarResponse(evaluated_topics_count=0, top_opportunities=[])

    # Resolver cliente y credenciales
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    resolved_model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if client is None:
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY no encontrada. Configúrala en .env o como variable de entorno."
            )
        genai_client = genai.Client(api_key=resolved_key)
    else:
        genai_client = client

    prompt = build_evaluation_prompt(articles, recent_topics=recent_history_topics)
    logger.info(
        "Invocando Gemini (%s) para evaluar %d artículos...",
        resolved_model,
        len(articles),
    )

    try:
        response = genai_client.models.generate_content(
            model=resolved_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=RadarResponse,
                temperature=0.2,
            ),
        )
    except Exception as e:
        logger.error("Error al invocar API de Gemini: %s", e)
        raise

    # Extracción y validación del modelo Pydantic
    radar_response: Optional[RadarResponse] = None
    if hasattr(response, "parsed") and isinstance(response.parsed, RadarResponse):
        radar_response = response.parsed
    elif hasattr(response, "text") and response.text:
        try:
            radar_response = RadarResponse.model_validate_json(response.text)
        except ValidationError as val_err:
            logger.warning(
                "Fallo al validar schema Pydantic directamente desde response.text: %s",
                val_err,
            )
            data = json.loads(response.text)
            radar_response = RadarResponse.model_validate(data)

    if radar_response is None:
        logger.error("No se pudo obtener una respuesta estructurada válida de Gemini.")
        return RadarResponse(evaluated_topics_count=len(articles), top_opportunities=[])

    # Post-procesamiento y filtrado determinista
    original_count = len(radar_response.top_opportunities)
    filtered = filter_and_rank_opportunities(
        radar_response.top_opportunities,
        min_virality=min_virality,
        min_feasibility=min_feasibility,
        max_items=max_opportunities,
    )
    radar_response.top_opportunities = filtered

    logger.info(
        "Evaluación completada: %d oportunidades sugeridas por el LLM, %d superaron los umbrales deterministas.",
        original_count,
        len(filtered),
    )
    return radar_response
