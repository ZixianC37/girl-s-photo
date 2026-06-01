"""Tests for event gateway endpoints and deduplication"""
from unittest.mock import MagicMock, AsyncMock, patch
import json


def test_feishu_url_verification(client):
    """Feishu challenge verification returns challenge"""
    resp = client.post("/webhook/feishu", json={"challenge": "abc123", "token": "test"})
    assert resp.status_code == 200
    assert resp.json() == {"challenge": "abc123"}


def test_feishu_url_verification_empty_challenge(client):
    """Feishu verification with empty challenge returns None challenge"""
    resp = client.post("/webhook/feishu", json={"challenge": "", "token": "test"})
    assert resp.status_code == 200
    assert resp.json() == {"challenge": ""}


def test_feishu_webhook_invalid_body(client):
    """POST /webhook/feishu with invalid body returns error"""
    resp = client.post("/webhook/feishu", json={})
    assert resp.status_code == 200  # Should return error status but 200 OK


def test_feishu_webhook_creates_task(client, db_session):
    """POST /webhook/feishu with valid event → 200 + task_instance created"""
    # Setup: create a route
    from app.models.tables import TaskRoute
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping='{}',
        enabled=True
    )
    db_session.add(route)
    db_session.commit()

    # Mock the task engine
    mock_engine = MagicMock()
    mock_engine.dispatch = AsyncMock()
    client.app.state.task_engine = mock_engine

    response = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_test", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {"任务标题": "Test"}}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_engine.dispatch.assert_called_once_with(
        table_id="tbl_test",
        record_id="rec_1",
        action="create",
        fields={"任务标题": "Test"}
    )


def test_feishu_webhook_no_route_found(client, db_session):
    """POST /webhook/feishu with no matching route → 200 (no-op)"""
    # Mock the task engine
    mock_engine = MagicMock()
    mock_engine.dispatch = AsyncMock(return_value=None)
    client.app.state.task_engine = mock_engine

    response = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_nonexistent", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {"任务标题": "Test"}}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_engine.dispatch.assert_called_once()


def test_feishu_webhook_disabled_route(client, db_session):
    """POST /webhook/feishu with disabled route → 200 (no-op)"""
    from app.models.tables import TaskRoute
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test_disabled",
        platform="dingtalk",
        group_id="group_1",
        field_mapping='{}',
        enabled=False  # Disabled
    )
    db_session.add(route)
    db_session.commit()

    mock_engine = MagicMock()
    mock_engine.dispatch = AsyncMock(return_value=None)
    client.app.state.task_engine = mock_engine

    response = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_test_disabled", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {"任务标题": "Test"}}
    })
    assert response.status_code == 200
    mock_engine.dispatch.assert_called_once()


def test_feishu_dedup(client):
    """Duplicate events are rejected"""
    mock_engine = MagicMock()
    mock_engine.dispatch = AsyncMock()
    client.app.state.task_engine = mock_engine

    body = {
        "event": {"table_id": "tbl_test_dedup", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {}}
    }
    resp1 = client.post("/webhook/feishu", json=body)
    resp2 = client.post("/webhook/feishu", json=body)

    assert resp1.status_code == 200
    assert resp1.json()["status"] == "ok"
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "duplicate"

    # First event should dispatch, second should not
    assert mock_engine.dispatch.call_count == 1


def test_feishu_dedup_different_actions(client):
    """Different actions on same record are not duplicates"""
    mock_engine = MagicMock()
    mock_engine.dispatch = AsyncMock()
    client.app.state.task_engine = mock_engine

    body1 = {
        "event": {"table_id": "tbl_test_actions", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {}}
    }
    body2 = {
        "event": {"table_id": "tbl_test_actions", "record_id": "rec_1", "action": "update"},
        "data": {"fields": {}}
    }

    resp1 = client.post("/webhook/feishu", json=body1)
    resp2 = client.post("/webhook/feishu", json=body2)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["status"] == "ok"
    assert resp2.json()["status"] == "ok"

    # Both should dispatch
    assert mock_engine.dispatch.call_count == 2


def test_feishu_dedup_different_records(client):
    """Different records are not duplicates"""
    mock_engine = MagicMock()
    mock_engine.dispatch = AsyncMock()
    client.app.state.task_engine = mock_engine

    body1 = {
        "event": {"table_id": "tbl_test_records", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {}}
    }
    body2 = {
        "event": {"table_id": "tbl_test_records", "record_id": "rec_2", "action": "create"},
        "data": {"fields": {}}
    }

    resp1 = client.post("/webhook/feishu", json=body1)
    resp2 = client.post("/webhook/feishu", json=body2)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["status"] == "ok"
    assert resp2.json()["status"] == "ok"

    # Both should dispatch
    assert mock_engine.dispatch.call_count == 2


def test_dingtalk_callback(client):
    """DingTalk callback triggers handle_callback"""
    mock_engine = MagicMock()
    mock_engine.handle_callback = AsyncMock()
    client.app.state.task_engine = mock_engine

    resp = client.post("/webhook/dingtalk/callback", json={
        "cardInstanceId": "card_1",
        "userId": "user_1",
        "params": {"action": "confirm"}
    })
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_engine.handle_callback.assert_called_once_with(
        platform="dingtalk",
        card_id="card_1",
        user_id="user_1",
        action="confirm"
    )


def test_dingtalk_callback_empty_action(client):
    """DingTalk callback with empty action still processes"""
    mock_engine = MagicMock()
    mock_engine.handle_callback = AsyncMock()
    client.app.state.task_engine = mock_engine

    resp = client.post("/webhook/dingtalk/callback", json={
        "cardInstanceId": "card_1",
        "userId": "user_1",
        "params": {}
    })
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_engine.handle_callback.assert_called_once_with(
        platform="dingtalk",
        card_id="card_1",
        user_id="user_1",
        action=""
    )


def test_dingtalk_callback_invalid_body(client):
    """DingTalk callback with invalid body returns error"""
    resp = client.post("/webhook/dingtalk/callback", json={})
    assert resp.status_code == 200  # Should process with empty values


def test_dingtalk_verify_get(client):
    """DingTalk GET verification returns status ok"""
    resp = client.get("/webhook/dingtalk/callback")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_dedup_is_duplicate():
    """Test EventDedup.is_duplicate marks and checks duplicates"""
    from app.gateway.dedup import EventDedup

    dedup = EventDedup(ttl=300)

    assert not dedup.is_duplicate("key1")  # First time, not duplicate
    dedup.mark_processed("key1")
    assert dedup.is_duplicate("key1")  # Now it's a duplicate
    assert not dedup.is_duplicate("key2")  # Different key, not duplicate


def test_dedup_cleanup():
    """Test EventDedup cleanup removes expired entries"""
    import time
    from app.gateway.dedup import EventDedup

    dedup = EventDedup(ttl=1)  # 1 second TTL

    dedup.mark_processed("key1")
    assert dedup.is_duplicate("key1")

    time.sleep(1.1)  # Wait for TTL to expire

    assert not dedup.is_duplicate("key1")  # Should be cleaned up


def test_dedup_cleanup_multiple():
    """Test EventDedup cleanup handles multiple expired entries"""
    import time
    from app.gateway.dedup import EventDedup

    dedup = EventDedup(ttl=1)

    dedup.mark_processed("key1")
    dedup.mark_processed("key2")
    dedup.mark_processed("key3")

    assert dedup.is_duplicate("key1")
    assert dedup.is_duplicate("key2")
    assert dedup.is_duplicate("key3")

    time.sleep(1.1)

    assert not dedup.is_duplicate("key1")
    assert not dedup.is_duplicate("key2")
    assert not dedup.is_duplicate("key3")


def test_feishu_parse_event_url_verification():
    """Test feishu.parse_event for URL verification"""
    from app.gateway.feishu import parse_event

    body = {"challenge": "test_challenge", "token": "test_token"}
    result = parse_event(body)

    assert result is not None
    assert result["type"] == "url_verification"
    assert result["challenge"] == "test_challenge"


def test_feishu_parse_event_data_change():
    """Test feishu.parse_event for data change event"""
    from app.gateway.feishu import parse_event

    body = {
        "event": {
            "table_id": "tbl_123",
            "record_id": "rec_456",
            "action": "update"
        },
        "data": {
            "fields": {"title": "Test Task", "status": "pending"}
        }
    }
    result = parse_event(body)

    assert result is not None
    assert result["type"] == "data_change"
    assert result["table_id"] == "tbl_123"
    assert result["record_id"] == "rec_456"
    assert result["action"] == "update"
    assert result["fields"] == {"title": "Test Task", "status": "pending"}


def test_feishu_parse_event_empty_body():
    """Test feishu.parse_event with empty body"""
    from app.gateway.feishu import parse_event

    assert parse_event({}) is None
    assert parse_event(None) is None


def test_feishu_parse_event_minimal():
    """Test feishu.parse_event with minimal event data"""
    from app.gateway.feishu import parse_event

    body = {"event": {}}
    result = parse_event(body)

    assert result is not None
    assert result["type"] == "data_change"
    assert result["table_id"] == ""
    assert result["record_id"] == ""
    assert result["action"] == "create"
    assert result["fields"] == {}


def test_dingtalk_parse_callback():
    """Test dingtalk.parse_callback extracts correct data"""
    from app.gateway.dingtalk import parse_callback

    body = {
        "cardInstanceId": "card_abc",
        "userId": "user_xyz",
        "params": {"action": "submit"}
    }
    result = parse_callback(body)

    assert result is not None
    assert result["card_id"] == "card_abc"
    assert result["user_id"] == "user_xyz"
    assert result["action"] == "submit"


def test_dingtalk_parse_callback_empty_body():
    """Test dingtalk.parse_callback with empty body"""
    from app.gateway.dingtalk import parse_callback

    assert parse_callback({}) is not None
    assert parse_callback(None) is None

    result = parse_callback({})
    assert result["card_id"] == ""
    assert result["user_id"] == ""
    assert result["action"] == ""


def test_dingtalk_parse_callback_no_params():
    """Test dingtalk.parse_callback without params"""
    from app.gateway.dingtalk import parse_callback

    body = {
        "cardInstanceId": "card_abc",
        "userId": "user_xyz"
    }
    result = parse_callback(body)

    assert result is not None
    assert result["card_id"] == "card_abc"
    assert result["user_id"] == "user_xyz"
    assert result["action"] == ""


def test_feishu_verify_token():
    """Test feishu.verify_token"""
    from app.config import settings
    from app.gateway.feishu import verify_token

    # Test with current settings
    result = verify_token(settings.feishu_verification_token)
    assert result is True

    # Test with wrong token
    result = verify_token("wrong_token")
    assert result is False
