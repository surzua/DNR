"""Carga y validación de la configuración efectiva del pipeline."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_CONFIG_PATH = Path("config/sources.yaml")


class PipelineConfigError(ValueError):
    """Indica que la configuración del pipeline es incompleta o inválida."""


@dataclass(frozen=True)
class PipelineConfig:
    """Parámetros que controlan una corrida completa del radar."""

    max_hours_lookback: int
    history_days_lookback: int
    max_opportunities_to_notify: int
    min_virality_score: int
    min_feasibility_score: int


def _required_int(values: Mapping[str, Any], key: str, *, minimum: int, maximum: int | None = None) -> int:
    """Lee y valida un entero obligatorio de la sección ``pipeline``."""
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PipelineConfigError(f"pipeline.{key} debe ser un entero.")
    if value < minimum or (maximum is not None and value > maximum):
        limit = f" entre {minimum} y {maximum}" if maximum is not None else f" mayor o igual a {minimum}"
        raise PipelineConfigError(f"pipeline.{key} debe ser{limit}.")
    return value


def load_pipeline_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> PipelineConfig:
    """Carga una única fuente de verdad para los parámetros del pipeline.

    Las fuentes RSS y Reddit conservan su propia lectura de configuración, pero los
    parámetros que afectan la selección de oportunidades se resuelven aquí y se
    propagan explícitamente a todas las fases de una corrida.
    """
    path = Path(config_path)
    if not path.exists():
        raise PipelineConfigError(f"Archivo de configuración no encontrado: {path}")

    try:
        with path.open("r", encoding="utf-8") as config_file:
            raw_config = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        raise PipelineConfigError(f"YAML inválido en {path}: {exc}") from exc
    except OSError as exc:
        raise PipelineConfigError(f"No se pudo leer {path}: {exc}") from exc

    pipeline = raw_config.get("pipeline") if isinstance(raw_config, dict) else None
    if not isinstance(pipeline, dict):
        raise PipelineConfigError("Falta la sección pipeline en la configuración.")

    return PipelineConfig(
        max_hours_lookback=_required_int(pipeline, "max_hours_lookback", minimum=1),
        history_days_lookback=_required_int(pipeline, "history_days_lookback", minimum=0),
        max_opportunities_to_notify=_required_int(pipeline, "max_opportunities_to_notify", minimum=1),
        min_virality_score=_required_int(pipeline, "min_virality_score", minimum=1, maximum=10),
        min_feasibility_score=_required_int(pipeline, "min_feasibility_score", minimum=1, maximum=10),
    )
