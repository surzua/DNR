"""Evaluador de oportunidades mediante Gemini API y Pydantic."""

import json
import logging
import os
from typing import Any, List, Literal, Optional, Set
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from src.analysis.prompt_templates import SYSTEM_PROMPT, build_evaluation_prompt
from src.storage.history_manager import normalize_title_for_dedup, normalize_url_for_dedup

load_dotenv()
logger = logging.getLogger("dnr.opportunity_eval")


class EvaluationResponseError(RuntimeError):
    """La respuesta del modelo no pudo convertirse en un resultado utilizable."""


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
    """Oportunidad editorial y de producto digital detectada.

    Los campos históricos describen el ángulo analítico. Los campos de producto
    permiten evaluar además para quién resuelve algo la oportunidad y qué MVP se
    podría publicar. Sus valores por defecto mantienen compatibles respuestas e
    historial creados antes de esta ampliación.
    """

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
    audience: str = Field(
        default="Audiencia general interesada en el tema",
        description="Persona o grupo específico al que sirve el producto",
    )
    user_need: str = Field(
        default="Entender el impacto del tema con información verificable",
        description="Necesidad concreta que la audiencia busca resolver",
    )
    user_action: str = Field(
        default="Explorar la información y obtener una respuesta útil",
        description="Acción concreta que podrá completar la persona usuaria",
    )
    product_type: Literal[
        "Visualización / explicador",
        "Calculadora",
        "Comparador",
        "Guía interactiva",
        "Planificador",
        "Simulador",
        "Verificador",
        "Análisis de datos",
    ] = Field(
        default="Análisis de datos",
        description="Tipo de producto; describe la utilidad, no la tecnología usada",
    )
    product_inputs: str = Field(
        default="Datos públicos y supuestos explícitos",
        description="Datos o decisiones mínimas que necesita el producto",
    )
    product_output: str = Field(
        default="Una respuesta o resultado interpretable para la audiencia",
        description="Resultado concreto que recibirá la persona usuaria",
    )
    share_reason: str = Field(
        default="Ayuda a otra persona a entender o resolver el mismo tema",
        description="Motivo específico por el que alguien compartiría el resultado",
    )
    evidence_status: Literal[
        "Propuesta (no verificada)",
        "Fuente localizada",
        "Verificada",
    ] = Field(
        default="Propuesta (no verificada)",
        description="Nivel de comprobación real de las fuentes o reglas necesarias",
    )
    validity_note: Optional[str] = Field(
        default=None,
        description="Fecha, condición de vencimiento o nota de vigencia del producto",
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


def _is_safe_http_url(url: Optional[str]) -> bool:
    """Verifica que la URL provenga de un protocolo web estándar (http/https)."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _article_field(article: Any, field_name: str) -> str:
    """Lee un campo textual desde un artículo tipado o diccionario."""
    value = article.get(field_name, "") if isinstance(article, dict) else getattr(article, field_name, "")
    return value.strip() if isinstance(value, str) else ""


def _verify_opportunity_inputs(opportunity: Opportunity, articles: List[Any]) -> bool:
    """Comprueba trazabilidad del detonante y una fuente mínima utilizable.

    No consulta la red: confirma que el LLM no inventó la noticia detonante y que
    existe al menos una fuente con URL HTTP(S) o una consulta de búsqueda concreta.
    La evidencia solo se eleva hasta ``Fuente localizada`` cuando se recibió una
    URL válida; una URL no prueba que el dataset sea correcto o esté vigente.
    """
    trigger_url = opportunity.trigger_article_url
    trigger_title = opportunity.trigger_article_title
    if not _is_safe_http_url(trigger_url) or not trigger_title:
        logger.info("Oportunidad descartada: detonante incompleto o URL no segura (%s).", opportunity.headline)
        return False

    normalized_url = normalize_url_for_dedup(trigger_url)
    normalized_title = normalize_title_for_dedup(trigger_title)
    matching_article = next(
        (
            article
            for article in articles
            if normalize_url_for_dedup(_article_field(article, "link")) == normalized_url
            and normalize_title_for_dedup(_article_field(article, "title")) == normalized_title
        ),
        None,
    )
    if matching_article is None:
        logger.info("Oportunidad descartada: detonante no corresponde a la ingesta (%s).", opportunity.headline)
        return False

    valid_sources: List[DataSource] = []
    has_located_url = False
    for source in opportunity.data_sources:
        reference = source.potential_url_or_query.strip()
        parsed_reference = urlparse(reference)
        if parsed_reference.scheme:
            if not _is_safe_http_url(reference):
                logger.info("Fuente descartada por URL no segura: %s.", source.name)
                continue
            has_located_url = True
        elif len(reference) < 3 or not any(char.isalnum() for char in reference):
            logger.info("Fuente descartada por referencia insuficiente: %s.", source.name)
            continue
        valid_sources.append(source)

    if not valid_sources:
        logger.info("Oportunidad descartada: no tiene una fuente o consulta utilizable (%s).", opportunity.headline)
        return False

    opportunity.data_sources = valid_sources
    opportunity.trigger_article_title = _article_field(matching_article, "title")
    opportunity.trigger_article_url = _article_field(matching_article, "link")
    opportunity.evidence_status = (
        "Fuente localizada" if has_located_url else "Propuesta (no verificada)"
    )
    return True


def filter_and_rank_opportunities(
    opportunities: List[Opportunity],
    min_virality: int = 7,
    min_feasibility: int = 6,
    max_items: int = 3,
    exclude_trigger_urls: Optional[Set[str]] = None,
    exclude_trigger_titles: Optional[Set[str]] = None,
    source_articles: Optional[List[Any]] = None,
) -> List[Opportunity]:
    """Filtra por umbrales, trazabilidad, fuentes mínimas, historial y duplicados.

    ``source_articles`` debe entregarse en producción para exigir que el detonante
    provenga de la ingesta; se mantiene opcional para reutilizar el filtro aislado.
    """
    valid: List[Opportunity] = []
    for opp in opportunities:
        if opp.virality_score >= min_virality and opp.technical_feasibility_score >= min_feasibility:
            # Blindaje contra enlaces inseguros o esquemas maliciosos
            if opp.trigger_article_url and not _is_safe_http_url(opp.trigger_article_url):
                logger.warning(
                    "Descartando trigger_article_url con esquema no seguro: %s",
                    opp.trigger_article_url,
                )
                opp.trigger_article_url = None

            norm_url = normalize_url_for_dedup(opp.trigger_article_url)
            norm_title = normalize_title_for_dedup(opp.trigger_article_title)

            # Exclusión por historial previo
            if exclude_trigger_urls and norm_url and norm_url in exclude_trigger_urls:
                logger.info("Oportunidad descartada por coincidir con URL de historial reciente: %s", opp.trigger_article_url)
                continue
            if exclude_trigger_titles and norm_title and norm_title in exclude_trigger_titles:
                logger.info("Oportunidad descartada por coincidir con titular de historial reciente: %s", opp.trigger_article_title)
                continue

            if source_articles is not None and not _verify_opportunity_inputs(opp, source_articles):
                continue

            valid.append(opp)

    # Ordenar por puntaje total combinado (viralidad + factibilidad técnica) y luego por viralidad
    valid.sort(
        key=lambda o: (o.virality_score + o.technical_feasibility_score, o.virality_score),
        reverse=True,
    )

    # Deduplicación intra-ejecución: si dos oportunidades provienen de la misma noticia detonante,
    # conservar únicamente la de mayor score.
    deduped: List[Opportunity] = []
    seen_run_urls: Set[str] = set()
    seen_run_titles: Set[str] = set()
    for opp in valid:
        norm_url = normalize_url_for_dedup(opp.trigger_article_url)
        norm_title = normalize_title_for_dedup(opp.trigger_article_title)

        if norm_url and norm_url in seen_run_urls:
            logger.info("Oportunidad descartada por duplicar noticia detonante en la misma corrida: %s", opp.trigger_article_url)
            continue
        if norm_title and norm_title in seen_run_titles:
            logger.info("Oportunidad descartada por duplicar titular detonante en la misma corrida: %s", opp.trigger_article_title)
            continue

        if norm_url:
            seen_run_urls.add(norm_url)
        if norm_title:
            seen_run_titles.add(norm_title)
        deduped.append(opp)

    return deduped[:max_items]


def evaluate_opportunities(
    articles: List[Any],
    recent_history_topics: Optional[List[str]] = None,
    recent_trigger_titles: Optional[List[str]] = None,
    exclude_trigger_urls: Optional[Set[str]] = None,
    exclude_trigger_titles: Optional[Set[str]] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    client: Optional[Any] = None,
    min_virality: int = 7,
    min_feasibility: int = 6,
    max_opportunities: int = 3,
    lookback_hours: int = 24,
    history_days: int = 2,
    timeout_ms: int = 90000,
) -> RadarResponse:
    """Evalúa candidatos de noticias utilizando Gemini y Structured Outputs Pydantic.

    Args:
        articles: Lista de objetos NewsArticle o diccionarios con noticias.
        recent_history_topics: Lista opcional de temas de los últimos días para deduplicar.
        api_key: Gemini API Key opcional (usa GEMINI_API_KEY del entorno por defecto).
        model_name: Nombre del modelo a usar (por defecto gemini-3.8-flash con fallbacks automáticos).
        client: Cliente de Gemini inyectable (útil para pruebas unitarias).
        min_virality: Puntaje mínimo de viralidad requerido (defecto: 7).
        min_feasibility: Puntaje mínimo de factibilidad técnica requerido (defecto: 6).
        max_opportunities: Máximo de oportunidades a retornar (defecto: 3).
        lookback_hours: Ventana de ingesta efectiva que se comunica al modelo.
        history_days: Ventana efectiva del historial que se comunica al modelo.
        timeout_ms: Timeout máximo por petición HTTP en milisegundos (defecto: 90000 ms).

    Returns:
        RadarResponse con la cantidad de temas evaluados y las mejores oportunidades filtradas.
    """
    if not articles:
        logger.info("No se proporcionaron artículos para evaluar. Retornando respuesta vacía.")
        return RadarResponse(evaluated_topics_count=0, top_opportunities=[])

    # Resolver cliente y credenciales
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    default_candidates = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]
    if model_name:
        candidate_models = [model_name] + [m for m in default_candidates if m != model_name]
    elif os.getenv("GEMINI_MODEL"):
        env_model = os.getenv("GEMINI_MODEL")
        candidate_models = [env_model] + [m for m in default_candidates if m != env_model]
    else:
        candidate_models = default_candidates

    if client is None:
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY no encontrada. Configúrala en .env o como variable de entorno."
            )
        genai_client = genai.Client(
            api_key=resolved_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        )
    else:
        genai_client = client

    prompt = build_evaluation_prompt(
        articles,
        recent_topics=recent_history_topics,
        recent_trigger_titles=recent_trigger_titles,
        lookback_hours=lookback_hours,
        history_days=history_days,
    )

    response = None
    last_error = None
    for model in candidate_models:
        try:
            logger.info(
                "Invocando Gemini (%s) para evaluar %d artículos...",
                model,
                len(articles),
            )
            response = genai_client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=RadarResponse,
                    temperature=0.2,
                ),
            )
            break
        except Exception as e:
            logger.warning("Fallo al consultar modelo %s: %s", model, e)
            last_error = e

    if response is None:
        logger.error("Todos los modelos candidatos de Gemini fallaron: %s", last_error)
        raise RuntimeError("Todos los modelos candidatos de Gemini fallaron.") from last_error

    # Extracción y validación del modelo Pydantic
    try:
        parsed_response = getattr(response, "parsed", None)
        if isinstance(parsed_response, RadarResponse):
            radar_response = parsed_response
        elif parsed_response is not None:
            radar_response = RadarResponse.model_validate(parsed_response)
        else:
            response_text = getattr(response, "text", None)
            if not response_text:
                raise EvaluationResponseError("Gemini no devolvió contenido estructurado.")
            radar_response = RadarResponse.model_validate_json(response_text)
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise EvaluationResponseError(
            "La respuesta de Gemini no cumple el esquema RadarResponse."
        ) from exc

    # Post-procesamiento y filtrado determinista
    original_count = len(radar_response.top_opportunities)
    filtered = filter_and_rank_opportunities(
        radar_response.top_opportunities,
        min_virality=min_virality,
        min_feasibility=min_feasibility,
        max_items=max_opportunities,
        exclude_trigger_urls=exclude_trigger_urls,
        exclude_trigger_titles=exclude_trigger_titles,
        source_articles=articles,
    )
    radar_response.top_opportunities = filtered

    logger.info(
        "Evaluación completada: %d oportunidades sugeridas por el LLM, %d superaron los umbrales deterministas.",
        original_count,
        len(filtered),
    )
    return radar_response
