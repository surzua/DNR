"""Tests for configuration files."""

from pathlib import Path
import yaml


def test_sources_yaml_structure():
    config_path = Path("config/sources.yaml")
    assert config_path.exists(), "config/sources.yaml must exist"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "rss_feeds" in config
    feeds = config["rss_feeds"]
    assert "cooperativa" in feeds
    assert "diario_financiero" in feeds
    assert "la_tercera" in feeds
    assert "biobiochile" in feeds

    assert "reddit" in config
    assert "chile" in config["reddit"]["subreddits"]

    assert "pipeline" in config
    assert config["pipeline"]["max_hours_lookback"] == 24
    assert config["pipeline"]["min_virality_score"] == 7
