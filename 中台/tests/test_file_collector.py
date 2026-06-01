"""Tests for FileCollector service"""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock

from app.services.file_collector import FileCollector
from app.models.tables import TaskInstance, TaskParticipant, FileRecord, TaskRoute


@pytest.fixture
def setup_file_task(db_session):
    """Create a task_instance with a participant in confirmed status"""
    route = TaskRoute(
        handler_name="RDTaskHandler", feishu_table_id="tbl_f",
        platform="dingtalk", group_id="g1", field_mapping="{}", enabled=True,
    )
    db_session.add(route)
    db_session.flush()

    instance = TaskInstance(
        handler_name="RDTaskHandler", route_id=route.id,
        feishu_record_id="r1", platform="dingtalk", group_id="g1",
        card_id="card_f", status="confirmed",
        flow_state='{"title": "样片拍摄", "deliverables": [{"name": "样片", "count": 2}]}',
    )
    db_session.add(instance)
    db_session.flush()

    participant = TaskParticipant(
        task_id=instance.id, platform_user_id="d_user_1",
        feishu_user_id="f_user_1", role="participant", status="confirmed",
    )
    db_session.add(participant)
    db_session.commit()

    return instance, participant


@pytest.mark.asyncio
async def test_route_message_file(db_session, setup_file_task):
    """File from user with active task → file recorded"""
    instance, participant = setup_file_task
    mock_adapter = MagicMock()
    mock_adapter.send_private_message = AsyncMock()

    collector = FileCollector(db_session, MagicMock(), {"dingtalk": mock_adapter})
    await collector.route_message(
        platform="dingtalk",
        user_id="d_user_1",
        conversation_id="cid_1",
        message={"msg_type": "file", "file_name": "photo.jpg", "download_code": "dl_123"},
    )

    files = db_session.query(FileRecord).all()
    assert len(files) == 1
    assert files[0].file_name == "photo.jpg"

    mock_adapter.send_private_message.assert_called_once()


@pytest.mark.asyncio
async def test_route_message_no_active_task(db_session):
    """User with no active tasks → reply 'no pending tasks'"""
    mock_adapter = MagicMock()
    mock_adapter.send_private_message = AsyncMock()

    collector = FileCollector(db_session, MagicMock(), {"dingtalk": mock_adapter})
    await collector.route_message(
        platform="dingtalk",
        user_id="unknown_user",
        conversation_id="cid_0",
        message={"msg_type": "file", "file_name": "test.pdf", "download_code": "dl_000"},
    )

    # No files recorded
    files = db_session.query(FileRecord).all()
    assert len(files) == 0

    # Should send "no active tasks" reply
    mock_adapter.send_private_message.assert_called_once()
    call_text = mock_adapter.send_private_message.call_args[0][1]
    assert "没有待处理" in call_text


@pytest.mark.asyncio
async def test_route_message_ignores_text(db_session):
    """Text messages are ignored"""
    mock_adapter = MagicMock()
    collector = FileCollector(db_session, MagicMock(), {"dingtalk": mock_adapter})
    await collector.route_message(
        platform="dingtalk",
        user_id="d_user_1",
        conversation_id="cid_1",
        message={"msg_type": "text", "content": "hello"},
    )

    files = db_session.query(FileRecord).all()
    assert len(files) == 0
