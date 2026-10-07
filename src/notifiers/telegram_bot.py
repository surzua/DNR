"""Despachador de mensajes a Telegram."""

from typing import Any, Dict, List


def send_telegram_alert(opportunity: Dict[str, Any]) -> bool:
    """Envía una oportunidad formateada a Telegram."""
    raise NotImplementedError("Will be implemented in upcoming steps")


def send_batch_alerts(opportunities: List[Dict[str, Any]]) -> int:
    """Envía un lote de oportunidades a Telegram."""
    raise NotImplementedError("Will be implemented in upcoming steps")
