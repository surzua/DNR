"""Parser de feeds RSS de prensa chilena."""

from typing import Any, Dict, List


def fetch_rss_feeds(config_path: str = "config/sources.yaml") -> List[Dict[str, Any]]:
    """Fetch and parse articles from configured Chilean RSS feeds."""
    raise NotImplementedError("Will be implemented in Step 2")
