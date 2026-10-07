"""Storage and history manager modules."""

from src.storage.articles_cache import load_articles_cache, save_articles_cache
from src.storage.history_manager import (
    HistoryEntry,
    generate_next_id,
    get_recent_topics,
    load_history,
    save_history,
)

__all__ = [
    "HistoryEntry",
    "load_history",
    "save_history",
    "get_recent_topics",
    "generate_next_id",
    "save_articles_cache",
    "load_articles_cache",
]
