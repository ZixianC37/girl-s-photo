"""DingTalk callback parsing and verification"""
from typing import Optional, Dict, Any


def parse_callback(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract structured data from DingTalk interactive card callback.

    Args:
        body: Raw JSON body from DingTalk callback request

    Returns:
        Structured callback dict with keys:
        - card_id: Interactive card instance ID
        - user_id: DingTalk user ID who triggered the callback
        - action: Action value from the callback

        Returns None if body is malformed
    """
    if body is None or not isinstance(body, dict):
        return None

    return {
        "card_id": body.get("cardInstanceId", ""),
        "user_id": body.get("userId", ""),
        "action": body.get("params", {}).get("action", ""),
    }


def parse_message_callback(body):
    """Extract data from DingTalk robot message callback (private chat)"""
    if not body or not isinstance(body, dict):
        return None

    msg_type = body.get("msgtype", "")
    sender_id = body.get("senderStaffId", "")
    conversation_id = body.get("conversationId", "")

    result = {
        "msg_type": msg_type,
        "sender_id": sender_id,
        "conversation_id": conversation_id,
    }

    if msg_type == "file":
        result["file_name"] = body.get("fileName", "")
        result["download_code"] = body.get("downloadCode", "")
    elif msg_type == "picture":
        result["download_code"] = body.get("downloadCode", "")
    elif msg_type == "text":
        text_content = body.get("text", {})
        result["content"] = text_content.get("content", "") if isinstance(text_content, dict) else ""

    return result
