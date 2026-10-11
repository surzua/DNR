"""Storage and history manager modules."""

from src.storage.articles_cache import load_articles_cache, save_articles_cache
from src.storage.history_manager import (
    HistoryEntry,
    filter_articles_by_history,
    generate_next_id,
    get_recent_topics,
    get_recent_trigger_titles,
    get_recent_trigger_urls,
    load_history,
    normalize_title_for_dedup,
    normalize_url_for_dedup,
    save_history,
)

__all__ = [
    "HistoryEntry",
    "load_history",
    "save_history",
    "get_recent_topics",
    "get_recent_trigger_urls",
    "get_recent_trigger_titles",
    "filter_articles_by_history",
    "normalize_url_for_dedup",
    "normalize_title_for_dedup",
    "generate_next_id",
    "save_articles_cache",
    "load_articles_cache",
]
