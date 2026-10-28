"""Evaluador de oportunidades mediante Gemini API y Pydantic."""

import json
import logging
import os
from datetime import datetime
from typing import Any, List, Literal, Optional, Set
from urllib.parse import urlparse
from types import SimpleNamespace
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from src.analysis.prompt_templates import SYSTEM_PROMPT, build_evaluation_prompt
from src.analysis.source_verification import verify_opportunities_sources
from src.storage.history_manager import normalize_title_for_dedup, normalize_url_for_dedup

load_dotenv()
logger = logging.getLogger("dnr.opportunity_eval")


class EvaluationResponseError(RuntimeError):
    """La respuesta del modelo no pudo convertirse en un resultado utilizable."""


def _evaluate_with_nvidia(prompt: str, api_key: str, timeout_ms: int) -> Any:
    """Consulta NVIDIA NIM; la respuesta se valida con el contrato común abajo."""
    model = os.getenv("NVIDIA_MODEL") or "meta/llama-3.3-70b-instruct"
    schema = json.dumps(GeminiRadarResponse.model_json_schema(), ensure_ascii=False)
    logger.info("Invocando NVIDIA NIM (%s) como respaldo...", model)
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt + "\n\nResponde únicamente con un objeto JSON válido que cumpla este esquema:\n" + schema},
            ],
            "temperature": 0.2,
            "max_tokens": 8192,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=timeout_ms / 1000,
    )
    response.raise_for_status()
    data = response.json()
    choice = data["choices"][0]
    if choice.get("finish_reason") == "length":
        raise EvaluationResponseError("NVIDIA devolvió una respuesta truncada.")
    return SimpleNamespace(parsed=None, text=choice["message"]["content"])


class DataSource(BaseModel):
    """Evidencia, regla o insumo requerido para construir la propuesta."""

    name: str = Field(description="Nombre descriptivo de la fuente o institución")
    type: Literal[
        "API Pública",
        "Tabla Wikipedia",
        "Portal Abierto",
        "Scraping HTML",
        "Dataset Descargable",
        "Regla o reglamento",
        "Documentación oficial",
        "Mecánica reproducible",
        "Fuente editorial",
    ] = Field(description="Tipo de acceso técnico a los datos")
    potential_url_or_query: str = Field(
        description="URL directa o término de búsqueda exacto para encontrar la data"
    )
    friction_level: Literal[
        "Baja (Horas)",
        "Media (1-2 días)",
        "Alta (Requiere peticiones de transparencia)",
    ] = Field(description="Estimación del tiempo y complejidad para obtener el dataset")
    verification_status: Literal["not_checked", "not_checkable", "accessible", "failed"] = Field(
        default="not_checked",
        description="Resultado de acceso técnico; no es una validación editorial",
    )
    verification_checked_at: Optional[datetime] = Field(default=None)
    verification_url: Optional[str] = Field(default=None)
    verification_http_status: Optional[int] = Field(default=None)
    verification_content_type: Optional[str] = Field(default=None)
    verification_error: Optional[str] = Field(default=None)
    editorial_status: Literal[
        "pending_review",
        "reported_by_trigger",
        "partially_supported",
        "supported",
        "contradicted",
        "not_applicable",
    ] = Field(
        default="pending_review",
        description="Estado editorial independiente del acceso HTTP",
    )
    supports_claims: List[str] = Field(
        default_factory=list,
        description="Afirmaciones concretas que este documento respalda o debe revisar",
    )
    evidence_location: Optional[str] = Field(
        default=None,
        description="Sección, tabla o fragmento consultado; vacío si no se revisó el contenido",
    )
    editorial_reviewed_at: Optional[datetime] = Field(default=None)
    source_validity_note: Optional[str] = Field(default=None)
    pending_checks: List[str] = Field(default_factory=list)


class OpportunityAssessment(BaseModel):
    """Rúbrica explícita para ordenar oportunidades sin fingir precisión.

    Cada dimensión se evalúa entre 0 y 5. Los valores cero indican que una
    respuesta antigua no proporcionó la dimensión; en ese caso el ranking
    mantiene el criterio histórico para conservar compatibilidad.
    """

    utility_score: int = Field(default=0, ge=0, le=5, description="Utilidad de la tarea para su audiencia")
    attention_score: int = Field(default=0, ge=0, le=5, description="Atención y oportunidad temporal observables")
    shareability_score: int = Field(default=0, ge=0, le=5, description="Claridad del motivo para compartir")
    differentiation_score: int = Field(default=0, ge=0, le=5, description="Mejora concreta frente a alternativas")
    speed_to_publish_score: int = Field(default=0, ge=0, le=5, description="Probabilidad de publicar con rapidez")
    durable_value_score: int = Field(default=0, ge=0, le=5, description="Valor después del pico de la noticia")
    confidence_score: int = Field(default=0, ge=0, le=5, description="Confianza en los supuestos disponibles")
    learning_value_score: int = Field(default=0, ge=0, le=5, description="Valor de aprendizaje al construir")

    def has_complete_rubric(self) -> bool:
        """Indica si la respuesta contiene todas las dimensiones solicitadas."""
        return all(
            score > 0
            for score in (
                self.utility_score,
                self.attention_score,
                self.shareability_score,
                self.differentiation_score,
                self.speed_to_publish_score,
                self.durable_value_score,
                self.confidence_score,
            )
        )

    def priority_score(self) -> Optional[float]:
        """Devuelve la prioridad ponderada o ``None`` si falta la rúbrica."""
        if not self.has_complete_rubric():
            return None
        return round(
            (
                self.utility_score * 0.25
                + self.attention_score * 0.20
                + self.shareability_score * 0.15
                + self.differentiation_score * 0.15
                + self.speed_to_publish_score * 0.15
                + self.durable_value_score * 0.10
            ),
            2,
        )


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
        "App web",
        "Experiencia interactiva",
        "Utilidad local",
        "Recurso descargable",
    ] = Field(description="Formato de entrega; no determina la tecnología")
    data_sources: List[DataSource] = Field(
        description="Fuentes de datos públicas necesarias"
    )
    virality_score: int = Field(
        ge=1, le=10, description="Potencial viral y de debate público (1-10)"
    )
    technical_feasibility_score: int = Field(
        ge=1, le=10, description="Viabilidad técnica del alcance mínimo (1-10)"
    )
    fast_execution_strategy: str = Field(
        description="Primeros pasos concretos para investigar y construir el alcance mínimo"
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
        "Juego o desafío",
        "Utilidad para archivos",
        "Recurso descargable",
        "Generador creativo",
        "Checklist",
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
    delivery_format: str = Field(
        default="App web o recurso local, según la interacción",
        description="Medio de entrega separado del tipo de producto y de la tecnología",
    )
    implementation_options: List[str] = Field(
        default_factory=list,
        description="Tecnologías posibles justificadas por la necesidad, nunca obligatorias",
    )
    first_interaction: str = Field(
        default="La persona abre el producto y realiza una acción breve para obtener valor",
        description="Primera acción de valor sin exigir registro o formularios largos",
    )
    differentiator: str = Field(
        default="Diferencia por comprobar frente a alternativas existentes",
        description="Mejora concreta o revisión pendiente de alternativas",
    )
    share_with: str = Field(
        default="Personas concretas a quienes les resuelve la misma necesidad",
        description="Destinatario específico del resultado, no una audiencia abstracta",
    )
    share_purpose: str = Field(
        default="Ayudar, coordinar o invitar a probar el producto",
        description="Para qué se compartiría el resultado",
    )
    share_mechanism: Literal[
        "Ayudar",
        "Coordinar",
        "Desafiar",
        "Comparar escenarios",
        "Expresar una creación",
        "Pendiente de revisión",
    ] = Field(default="Pendiente de revisión")
    shareable_artifact: Optional[str] = Field(
        default=None,
        description="Enlace, imagen, archivo o desafío reproducible solo cuando aporta valor",
    )
    alternatives_review_status: Literal["pending", "reviewed", "not_applicable"] = Field(
        default="pending",
        description="No afirmar unicidad si aún no se revisaron alternativas",
    )
    assessment_reasons: List[str] = Field(
        default_factory=list,
        description="Lista de justificaciones breves para puntajes de atención, utilidad y difusión; no probabilidades",
    )
    scope_class: Literal["prototipo_breve", "varias_sesiones", "demasiado_grande"] = Field(
        default="prototipo_breve",
        description="Alcance orientativo, no una promesa de tiempo",
    )
    minimum_version: str = Field(
        default="Una interacción central comprobable con datos, regla o mecánica explícita",
        description="Qué construir primero para validar la propuesta",
    )
    explicit_limits: List[str] = Field(
        default_factory=list,
        description="Qué queda fuera de la primera versión",
    )
    optional_extension: Optional[str] = Field(default=None)
    learning_skill: str = Field(
        default="La habilidad depende de la tecnología y evidencia finalmente elegidas",
        description="Habilidad concreta que la construcción permitiría practicar",
    )
    prior_knowledge: str = Field(
        default="Si se desconocen las habilidades del creador, indicar requisitos de forma condicional",
    )
    technical_difficulty: Literal["baja", "media", "alta"] = Field(default="media")
    verification_effort: Literal["bajo", "medio", "alto"] = Field(default="medio")
    difficulty_reason: str = Field(
        default="Explicar por separado complejidad técnica y trabajo de comprobación",
    )
    manual_steps: List[str] = Field(
        default_factory=list,
        description="Pasos manuales de investigación, diseño, implementación y validación",
    )
    technical_dependencies: List[str] = Field(default_factory=list)
    validation_cases: List[str] = Field(
        default_factory=list,
        description="Casos para comprobar cálculos, reglas o mecánica antes de compartir",
    )
    evidence_status: Literal[
        "Pendiente de revisión",
        "Respaldo parcial",
        "Lista para construir",
        "Propuesta (no verificada)",
        "Fuente localizada",
        "Verificada",
    ] = Field(
        default="Pendiente de revisión",
        description="Estado editorial de evidencia; no se infiere desde HTTP",
    )
    validity_note: Optional[str] = Field(
        default=None,
        description="Fecha, condición de vencimiento o nota de vigencia del producto",
    )
    known_facts: List[str] = Field(
        default_factory=list,
        description="Hechos del detonante; no incluyen conclusiones aún no comprobadas",
    )
    hypotheses_to_test: List[str] = Field(
        default_factory=list,
        description="Preguntas o hipótesis que el producto debe comprobar, no afirmar",
    )
    verification_plan: List[str] = Field(
        default_factory=list,
        description="Comprobaciones de variables, período, cobertura y límites antes de publicar",
    )
    reported_facts: List[str] = Field(
        default_factory=list,
        description="Lo que reporta el detonante, sin elevarlo a hecho contrastado",
    )
    corroborated_facts: List[str] = Field(
        default_factory=list,
        description="Hechos contrastados con evidencia revisada; vacíos si no se consultó el contenido",
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Supuestos explícitos que no deben comunicarse como hallazgos",
    )
    critical_claims: List[str] = Field(
        default_factory=list,
        description="Reglas o datos que deben tener respaldo antes de construir o compartir",
    )
    distribution_channel: Optional[str] = Field(
        default=None,
        description="Canal inicial concreto para distribuir el producto",
    )
    existing_alternatives: Optional[str] = Field(
        default=None,
        description="Alternativas existentes y mejora específica que ofrece el producto",
    )
    assessment: OpportunityAssessment = Field(
        default_factory=OpportunityAssessment,
        description="Rúbrica explícita para comparar utilidad, atención, difusión y factibilidad",
    )

    def priority_score(self) -> float:
        """Obtiene una prioridad comparable, con fallback para registros antiguos."""
        rubric_score = self.assessment.priority_score()
        if rubric_score is not None:
            return rubric_score
        return round((self.virality_score + self.technical_feasibility_score) / 4, 2)


class RejectedOpportunity(BaseModel):
    """Candidato descartado por un filtro determinista y su motivo auditable."""

    opportunity: Opportunity
    reason: str = Field(description="Motivo concreto del descarte")


class RadarResponse(BaseModel):
    """Estructura de respuesta completa del evaluador de radar."""

    evaluated_topics_count: int = Field(
        description="Cantidad aproximada de temas o noticias analizadas"
    )
    top_opportunities: List[Opportunity] = Field(
        default_factory=list,
        description="Oportunidades destacadas que superaron los umbrales de viabilidad",
    )
    rejected_opportunities: List[RejectedOpportunity] = Field(
        default_factory=list,
        description="Candidatos descartados por los filtros deterministas del pipeline",
    )


class GeminiDataSource(BaseModel):
    """Contrato acotado para Structured Output compatible con Gemini Developer API."""

    name: str
    type: str
    potential_url_or_query: str
    friction_level: str


class GeminiOpportunity(BaseModel):
    """Campos esenciales que Gemini debe entregar; Opportunity completa los defaults."""

    headline: str
    category: str
    why_is_trending: str
    contrarian_or_curious_angle: str
    suggested_deliverable: str
    data_sources: List[GeminiDataSource]
    virality_score: int
    technical_feasibility_score: int
    fast_execution_strategy: str
    trigger_article_title: str
    trigger_article_url: str


class GeminiRadarResponse(BaseModel):
    evaluated_topics_count: int
    top_opportunities: List[GeminiOpportunity]


def _match_choice(value: str, choices: tuple[str, ...], fallback: str) -> str:
    """Normaliza valores flexibles del modelo al contrato estricto del dominio."""
    normalized = value.strip().casefold()
    return next((choice for choice in choices if choice.casefold() == normalized), fallback)


def _to_radar_response(gemini_response: GeminiRadarResponse) -> RadarResponse:
    categories = ("Economía & Finanzas", "Política & Estado", "Deportes", "Sociedad & Tendencias")
    deliverables = (
        "Gráfico Estático de Alto Impacto", "App Interactiva (Streamlit)",
        "Análisis Predictivo/Optimización", "App web", "Experiencia interactiva",
        "Utilidad local", "Recurso descargable",
    )
    source_types = (
        "API Pública", "Tabla Wikipedia", "Portal Abierto", "Scraping HTML",
        "Dataset Descargable", "Regla o reglamento", "Documentación oficial",
        "Mecánica reproducible", "Fuente editorial",
    )
    friction_levels = (
        "Baja (Horas)", "Media (1-2 días)", "Alta (Requiere peticiones de transparencia)",
    )
    opportunities = []
    for candidate in gemini_response.top_opportunities:
        payload = candidate.model_dump()
        payload["category"] = _match_choice(payload["category"], categories, "Sociedad & Tendencias")
        payload["suggested_deliverable"] = _match_choice(
            payload["suggested_deliverable"], deliverables, "Análisis Predictivo/Optimización"
        )
        payload["trigger_article_title"] = payload["trigger_article_title"] or None
        payload["trigger_article_url"] = payload["trigger_article_url"] or None
        payload["data_sources"] = [
            {
                **source.model_dump(),
                "type": _match_choice(source.type, source_types, "Portal Abierto"),
                "friction_level": _match_choice(source.friction_level, friction_levels, "Media (1-2 días)"),
            }
            for source in candidate.data_sources
        ]
        opportunities.append(Opportunity.model_validate(payload))
    return RadarResponse(
        evaluated_topics_count=gemini_response.evaluated_topics_count,
        top_opportunities=opportunities,
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


def _opportunity_signature(opportunity: Opportunity) -> str:
    """Resume producto, necesidad y acción para deduplicar propuestas reales."""
    parts = (
        opportunity.product_type,
        opportunity.user_need,
        opportunity.user_action,
        opportunity.product_output,
    )
    trigger = normalize_url_for_dedup(opportunity.trigger_article_url) or normalize_title_for_dedup(
        opportunity.trigger_article_title
    )
    # Sin detonante no hay base para fusionar dos respuestas aisladas: preservar
    # candidatos distintos es más seguro que descartarlos por defaults heredados.
    trigger = trigger or normalize_title_for_dedup(opportunity.headline)
    return "|".join((trigger, *(normalize_title_for_dedup(part) for part in parts)))


def _verify_opportunity_inputs(opportunity: Opportunity, articles: List[Any]) -> bool:
    """Comprueba trazabilidad del detonante y una fuente mínima utilizable.

    No consulta la red: confirma que el LLM no inventó la noticia detonante y que
    existe al menos una fuente con URL HTTP(S) o una consulta de búsqueda concreta.
    Una URL no cambia el estado editorial: solo deja un respaldo localizable para
    revisión humana posterior.
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
    for source in opportunity.data_sources:
        reference = source.potential_url_or_query.strip()
        parsed_reference = urlparse(reference)
        if parsed_reference.scheme:
            if not _is_safe_http_url(reference):
                logger.info("Fuente descartada por URL no segura: %s.", source.name)
                continue
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
    # Nunca promocionar evidencia editorial desde la forma de una URL. Conservamos
    # el estado proporcionado por la evaluación, que por defecto es pendiente.
    return True


def filter_and_rank_opportunities(
    opportunities: List[Opportunity],
    min_virality: int = 7,
    min_feasibility: int = 6,
    max_items: int = 3,
    exclude_trigger_urls: Optional[Set[str]] = None,
    exclude_trigger_titles: Optional[Set[str]] = None,
    source_articles: Optional[List[Any]] = None,
    rejected: Optional[List[RejectedOpportunity]] = None,
) -> List[Opportunity]:
    """Filtra por umbrales, trazabilidad, fuentes mínimas, historial y duplicados.

    ``source_articles`` debe entregarse en producción para exigir que el detonante
    provenga de la ingesta; se mantiene opcional para reutilizar el filtro aislado.
    """
    valid: List[Opportunity] = []

    def reject(opportunity: Opportunity, reason: str) -> None:
        logger.info("Oportunidad descartada (%s): %s", reason, opportunity.headline)
        if rejected is not None:
            rejected.append(RejectedOpportunity(opportunity=opportunity, reason=reason))

    for opp in opportunities:
        if opp.virality_score < min_virality:
            reject(opp, "viralidad_bajo_umbral")
            continue
        if opp.technical_feasibility_score < min_feasibility:
            reject(opp, "factibilidad_bajo_umbral")
            continue

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
            reject(opp, "noticia_detonante_ya_evaluada")
            continue
        if exclude_trigger_titles and norm_title and norm_title in exclude_trigger_titles:
            reject(opp, "titular_detonante_ya_evaluado")
            continue

        if source_articles is not None and not _verify_opportunity_inputs(opp, source_articles):
            reject(opp, "trazabilidad_o_fuente_minima_invalida")
            continue

        valid.append(opp)

    # La rúbrica ordena por utilidad real y posibilidad de distribución, sin
    # eliminar los gates ya existentes de viralidad, factibilidad y evidencia.
    # Las respuestas antiguas, que no incluyen rúbrica, conservan un fallback
    # normalizado de los dos puntajes históricos.
    valid.sort(
        key=lambda o: (
            o.priority_score(),
            o.assessment.confidence_score,
            o.virality_score + o.technical_feasibility_score,
            o.virality_score,
        ),
        reverse=True,
    )

    # Deduplicación intra-ejecución por producto y necesidad, no por detonante: un
    # mismo evento puede justificar alternativas sustancialmente distintas.
    deduped: List[Opportunity] = []
    seen_signatures: Set[str] = set()
    for opp in valid:
        signature = _opportunity_signature(opp)
        if signature and signature in seen_signatures:
            reject(opp, "producto_y_necesidad_duplicados_en_corrida")
            continue
        if signature:
            seen_signatures.add(signature)
        deduped.append(opp)

    accepted = deduped[:max_items]
    for opp in deduped[max_items:]:
        reject(opp, "prioridad_menor_que_limite_de_alertas")
    return accepted


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
    verify_sources: bool = False,
    require_verified_source: bool = False,
    source_verification_timeout_seconds: int = 10,
) -> RadarResponse:
    """Evalúa noticias con NVIDIA primero y usa Gemini como respaldo.

    Args:
        articles: Lista de objetos NewsArticle o diccionarios con noticias.
        recent_history_topics: Lista opcional de temas de los últimos días para deduplicar.
        api_key: Gemini API Key opcional (usa GEMINI_API_KEY del entorno por defecto).
        model_name: Modelo Gemini inicial si NVIDIA falla (con fallbacks automáticos).
        client: Cliente de Gemini inyectable (útil para pruebas unitarias).
        min_virality: Puntaje mínimo de viralidad requerido (defecto: 7).
        min_feasibility: Puntaje mínimo de factibilidad técnica requerido (defecto: 6).
        max_opportunities: Máximo de oportunidades a retornar (defecto: 3).
        lookback_hours: Ventana de ingesta efectiva que se comunica al modelo.
        history_days: Ventana efectiva del historial que se comunica al modelo.
        timeout_ms: Timeout máximo por petición HTTP en milisegundos (defecto: 90000 ms).
        verify_sources: Comprueba técnicamente las URLs de datos antes de retornar.
        require_verified_source: Compatibilidad: descarta oportunidades sin URL accesible si se activa.
        source_verification_timeout_seconds: Límite por consulta de fuente.

    Returns:
        RadarResponse con la cantidad de temas evaluados y las mejores oportunidades filtradas.
    """
    if not articles:
        logger.info("No se proporcionaron artículos para evaluar. Retornando respuesta vacía.")
        return RadarResponse(evaluated_topics_count=0, top_opportunities=[])

    # Resolver cliente y credenciales
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    # Mantener alternativas que están disponibles para esta API. Los aliases y
    # modelos retirados para cuentas nuevas no son fallbacks confiables.
    default_candidates = [
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.7-flash",
    ]
    if model_name:
        candidate_models = [model_name] + [m for m in default_candidates if m != model_name]
    elif os.getenv("GEMINI_MODEL"):
        env_model = os.getenv("GEMINI_MODEL")
        candidate_models = [env_model] + [m for m in default_candidates if m != env_model]
    else:
        candidate_models = default_candidates

    if client is None:
        if not resolved_key and not nvidia_key:
            raise ValueError(
                "Configura NVIDIA_API_KEY o GEMINI_API_KEY en .env o como variable de entorno."
            )
        genai_client = genai.Client(
            api_key=resolved_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        ) if resolved_key else None
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
    provider = "NVIDIA"
    if nvidia_key:
        try:
            response = _evaluate_with_nvidia(prompt, nvidia_key, timeout_ms)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, EvaluationResponseError) as exc:
            logger.warning("Falló NVIDIA; se continuará con Gemini (%s).", type(exc).__name__)
            last_error = exc

    for model in candidate_models if response is None and genai_client is not None else []:
        try:
            logger.info(
                "Invocando Gemini (%s) para evaluar %d artículos...",
                model,
                len(articles),
            )
            provider = "Gemini"
            try:
                response = genai_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=GeminiRadarResponse,
                        temperature=0.2,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
            except Exception as exc:
                # Algunos modelos del Developer API rechazan esquemas Pydantic
                # válidos con un 400 genérico. Pedir JSON y validarlo abajo con
                # RadarResponse conserva el contrato sin bloquear el radar.
                if "INVALID_ARGUMENT" not in str(exc):
                    raise
                logger.warning(
                    "El modelo %s rechazó la salida estructurada; se reintenta con JSON validado localmente.",
                    model,
                )
                response = genai_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.2,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    ),
                )
            break
        except Exception as e:
            logger.warning("Fallo al consultar modelo %s: %s", model, e)
            last_error = e

    if response is None:
        logger.error("Fallaron los proveedores configurados; último error: %s", last_error)
        raise RuntimeError("Fallaron NVIDIA y todos los modelos candidatos de Gemini.") from last_error

    # Extracción y validación del modelo Pydantic
    try:
        parsed_response = getattr(response, "parsed", None)
        if isinstance(parsed_response, RadarResponse):
            radar_response = parsed_response
        elif isinstance(parsed_response, GeminiRadarResponse):
            radar_response = _to_radar_response(parsed_response)
        elif parsed_response is not None:
            radar_response = _to_radar_response(GeminiRadarResponse.model_validate(parsed_response))
        else:
            response_text = getattr(response, "text", None)
            if not response_text:
                raise EvaluationResponseError(f"{provider} no devolvió contenido estructurado.")
            radar_response = _to_radar_response(GeminiRadarResponse.model_validate_json(response_text))
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise EvaluationResponseError(
            f"La respuesta de {provider} no cumple el esquema RadarResponse."
        ) from exc

    # Post-procesamiento y filtrado determinista. Los descartes los calcula el
    # pipeline; no se aceptan razones generadas por el modelo como auditoría.
    radar_response.rejected_opportunities = []
    original_count = len(radar_response.top_opportunities)
    filtered = filter_and_rank_opportunities(
        radar_response.top_opportunities,
        min_virality=min_virality,
        min_feasibility=min_feasibility,
        max_items=max_opportunities,
        exclude_trigger_urls=exclude_trigger_urls,
        exclude_trigger_titles=exclude_trigger_titles,
        source_articles=articles,
        rejected=radar_response.rejected_opportunities,
    )
    if require_verified_source and not verify_sources:
        raise ValueError("require_verified_source necesita verify_sources=True.")
    if verify_sources and filtered:
        verified_by_opportunity = verify_opportunities_sources(
            filtered,
            timeout_seconds=source_verification_timeout_seconds,
        )
        if require_verified_source:
            before_verification = len(filtered)
            accessible: List[Opportunity] = []
            for opp in filtered:
                if verified_by_opportunity.get(id(opp), False):
                    accessible.append(opp)
                else:
                    radar_response.rejected_opportunities.append(
                        RejectedOpportunity(
                            opportunity=opp,
                            reason="fuente_url_no_accesible",
                        )
                    )
            filtered = accessible
            if len(filtered) < before_verification:
                logger.info(
                    "Comprobación técnica descartó %d oportunidades sin una URL accesible.",
                    before_verification - len(filtered),
                )
        # El acceso HTTP queda en cada DataSource. Jamás eleva evidence_status:
        # una respuesta 200 no demuestra que una afirmación sea correcta, vigente
        # ni que el documento respalde la interpretación propuesta.
    radar_response.top_opportunities = filtered

    logger.info(
        "Evaluación completada: %d oportunidades sugeridas por el LLM, %d aceptadas y %d descartadas por filtros deterministas.",
        original_count,
        len(filtered),
        len(radar_response.rejected_opportunities),
    )
    return radar_response
