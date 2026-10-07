"""Manejo de lectura/escritura y deduplicación de historial."""

import json
from pathlib import Path
from typing import Any, Dict, List


HISTORY_FILE_PATH = Path("data/history.json")


def load_history(filepath: Path = HISTORY_FILE_PATH) -> List[Dict[str, Any]]:
    """Carga el historial de oportunidades analizadas."""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_history(history: List[Dict[str, Any]], filepath: Path = HISTORY_FILE_PATH) -> None:
    """Guarda el historial de oportunidades en el archivo JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
