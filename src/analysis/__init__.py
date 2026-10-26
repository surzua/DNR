"""Analysis and LLM evaluation engine modules."""

from src.analysis.opportunity_eval import (
    DataSource,
    EvaluationResponseError,
    Opportunity,
    RadarResponse,
    evaluate_opportunities,
    filter_and_rank_opportunities,
)
from src.analysis.prompt_templates import (
    SYSTEM_PROMPT,
    build_evaluation_prompt,
    format_article_snippet,
)
from src.analysis.source_verification import (
    SourceCheck,
    validate_public_http_url,
    verify_opportunities_sources,
    verify_opportunity_sources,
    verify_source_url,
)

__all__ = [
    "DataSource",
    "EvaluationResponseError",
    "Opportunity",
    "RadarResponse",
    "evaluate_opportunities",
    "filter_and_rank_opportunities",
    "SYSTEM_PROMPT",
    "build_evaluation_prompt",
    "format_article_snippet",
    "SourceCheck",
    "validate_public_http_url",
    "verify_source_url",
    "verify_opportunity_sources",
    "verify_opportunities_sources",
]
