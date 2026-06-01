"""Feishu webhook event parsing and verification"""
from typing import Optional, Dict, Any
from app.config import settings


def verify_token(token: str) -> bool:
    """
    Verify Feishu webhook verification token.

    Args:
        token: Token from Feishu webhook request

    Returns:
        True if token matches configured verification token
    """
    return token == settings.feishu_verification_token


def parse_event(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract structured event from Feishu webhook body.

    Handles two types of events:
    1. URL verification challenge (for webhook setup)
    2. Data table change events (for task dispatch)

    Args:
        body: Raw JSON body from Feishu webhook

    Returns:
        Structured event dict with keys:
        - type: "url_verification" or "data_change"
        - challenge: (only for url_verification) challenge string to echo back
        - table_id: (only for data_change) Feishu table ID
        - record_id: (only for data_change) Feishu record ID
        - action: (only for data_change) "create", "update", or "delete"
        - fields: (only for data_change) Dictionary of field values

        Returns None if body is malformed
    """
    if not body or not isinstance(body, dict):
        return None

    # Handle Feishu URL verification challenge
    if "challenge" in body:
        return {
            "type": "url_verification",
            "challenge": body.get("challenge")
        }

    # Extract data change event
    event = body.get("event", {})

    return {
        "type": "data_change",
        "table_id": event.get("table_id", ""),
        "record_id": event.get("record_id", ""),
        "action": event.get("action", "create"),
        "fields": body.get("data", {}).get("fields", {}),
    }
