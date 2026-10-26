"""Tests for configuration files."""

from pathlib import Path
import yaml
import pytest

from src.config import PipelineConfigError, load_pipeline_config


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


def test_load_pipeline_config_uses_declared_values():
    config = load_pipeline_config()

    assert config.max_hours_lookback == 24
    assert config.history_days_lookback == 2
    assert config.max_opportunities_to_notify == 3
    assert config.min_virality_score == 7
    assert config.min_feasibility_score == 6
    assert config.verify_source_urls is True
    assert config.require_verified_source is True
    assert config.source_verification_timeout_seconds == 10


def test_load_pipeline_config_rejects_invalid_values(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        "pipeline:\n"
        "  max_hours_lookback: 0\n"
        "  history_days_lookback: 2\n"
        "  max_opportunities_to_notify: 3\n"
        "  min_virality_score: 7\n"
        "  min_feasibility_score: 6\n",
        encoding="utf-8",
    )

    with pytest.raises(PipelineConfigError, match="max_hours_lookback"):
        load_pipeline_config(config_path)


def test_load_pipeline_config_rejects_verified_source_requirement_without_check(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        "pipeline:\n"
        "  max_hours_lookback: 24\n"
        "  history_days_lookback: 2\n"
        "  max_opportunities_to_notify: 3\n"
        "  min_virality_score: 7\n"
        "  min_feasibility_score: 6\n"
        "  verify_source_urls: false\n"
        "  require_verified_source: true\n",
        encoding="utf-8",
    )

    with pytest.raises(PipelineConfigError, match="require_verified_source"):
        load_pipeline_config(config_path)
