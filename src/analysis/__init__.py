"""Analysis and LLM evaluation engine modules."""

from src.analysis.opportunity_eval import (
    DataSource,
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

__all__ = [
    "DataSource",
    "Opportunity",
    "RadarResponse",
    "evaluate_opportunities",
    "filter_and_rank_opportunities",
    "SYSTEM_PROMPT",
    "build_evaluation_prompt",
    "format_article_snippet",
]
