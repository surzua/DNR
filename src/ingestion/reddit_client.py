"""Scraper ligero de Reddit vía endpoints JSON públicos."""

from typing import Any, Dict, List


def fetch_reddit_threads(config_path: str = "config/sources.yaml") -> List[Dict[str, Any]]:
    """Fetch high engagement threads from configured Chilean subreddits."""
    raise NotImplementedError("Will be implemented in upcoming steps")
