"""FastAPI routes for webhook endpoints"""
from fastapi import APIRouter, Request, Response
from app.gateway.dedup import EventDedup
from app.gateway import feishu, dingtalk

router = APIRouter(prefix="/webhook", tags=["webhook"])
dedup = EventDedup()


@router.post("/feishu")
async def feishu_webhook(request: Request):
    """
    Handle Feishu webhook events.

    Supports two event types:
    1. URL verification: Echoes back challenge for webhook setup
    2. Data changes: Dispatches events to task engine with deduplication

    Request body varies by event type:
    - URL verification: {"challenge": "...", "token": "..."}
    - Data change: {"event": {"table_id": "...", "record_id": "...", "action": "..."}, "data": {"fields": {...}}}
    """
    body = await request.json()

    # Parse event
    parsed = feishu.parse_event(body)
    if not parsed:
        return {"status": "error", "message": "Invalid event"}

    # Handle URL verification
    if parsed.get("type") == "url_verification":
        return {"challenge": parsed.get("challenge")}

    # Dedup check
    event_key = f"feishu:{parsed['table_id']}:{parsed['record_id']}:{parsed['action']}"
    if dedup.is_duplicate(event_key):
        return {"status": "duplicate"}
    dedup.mark_processed(event_key)

    # Dispatch to task engine
    engine = request.app.state.task_engine
    if engine:
        await engine.dispatch(
            table_id=parsed["table_id"],
            record_id=parsed["record_id"],
            action=parsed["action"],
            fields=parsed["fields"]
        )

    return {"status": "ok"}


@router.post("/dingtalk/callback")
async def dingtalk_callback(request: Request):
    """
    Handle DingTalk interactive card callbacks.

    Processes user actions on interactive cards and forwards them
    to the task engine for state updates.

    Request body:
    {
        "cardInstanceId": "...",
        "userId": "...",
        "params": {"action": "..."}
    }
    """
    body = await request.json()
    parsed = dingtalk.parse_callback(body)
    if not parsed:
        return {"status": "error"}

    # Forward to task engine
    engine = request.app.state.task_engine
    if engine:
        await engine.handle_callback(
            platform="dingtalk",
            card_id=parsed["card_id"],
            user_id=parsed["user_id"],
            action=parsed["action"]
        )

    return {"status": "ok"}


@router.get("/dingtalk/callback")
async def dingtalk_verify():
    """
    Handle DingTalk URL verification.

    DingTalk sends a GET request during webhook setup to verify the endpoint.
    """
    return {"status": "ok"}


@router.post("/dingtalk/message")
async def dingtalk_message(request: Request):
    """Handle DingTalk robot private message callback"""
    body = await request.json()
    parsed = dingtalk.parse_message_callback(body)
    if not parsed:
        return {"status": "error"}

    engine = request.app.state.task_engine
    if engine:
        await engine.handle_private_message(
            platform="dingtalk",
            user_id=parsed["sender_id"],
            conversation_id=parsed.get("conversation_id", ""),
            message=parsed,
        )

    return {"status": "ok"}
