"""Tests for TaskEngine"""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.engine.task_engine import TaskEngine
from app.models.tables import TaskRoute, TaskInstance, TaskParticipant
from app.models.types import TaskData, TaskUpdate, CardData, CardSection, CardAction, FlowDefinition


@pytest.mark.asyncio
async def test_dispatch_creates_task_instance(db_session):
    """Event for known route → creates task_instance + calls handler"""
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.commit()

    # Mock handler behavior
    mock_handler_instance = MagicMock()
    mock_handler_instance.parse_event.return_value = TaskData(
        title="Test",
        participants=["user_1", "user_2"],
        deadline=None,
        parameters={}
    )
    mock_handler_instance.get_flow.return_value = FlowDefinition(
        states=["pending", "confirmed"],
        initial="pending"
    )
    mock_handler_instance.build_card.return_value = CardData(
        title="Card",
        sections=[],
        actions=[]
    )

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_123")

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    result = await engine.dispatch(
        table_id="tbl_test",
        record_id="rec_1",
        action="create",
        fields={}
    )

    assert result is not None
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    assert instances[0].handler_name == "MockHandler"
    assert instances[0].card_id == "card_123"
    assert instances[0].status == "pending"

    # Check participants were created
    participants = db_session.query(TaskParticipant).all()
    assert len(participants) == 2
    assert all(p.role == "participant" for p in participants)
    assert all(p.status == "pending" for p in participants)


@pytest.mark.asyncio
async def test_dispatch_returns_none_for_unknown_route(db_session):
    """Unknown table_id → returns None without creating anything"""
    mock_registry = MagicMock()
    mock_adapter = MagicMock()

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    result = await engine.dispatch(
        table_id="tbl_unknown",
        record_id="rec_1",
        action="create",
        fields={}
    )

    assert result is None
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 0


@pytest.mark.asyncio
async def test_dispatch_returns_none_for_disabled_route(db_session):
    """Disabled route → returns None without creating anything"""
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping="{}",
        enabled=False
    )
    db_session.add(route)
    db_session.commit()

    mock_registry = MagicMock()
    mock_adapter = MagicMock()

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    result = await engine.dispatch(
        table_id="tbl_test",
        record_id="rec_1",
        action="create",
        fields={}
    )

    assert result is None
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 0


@pytest.mark.asyncio
async def test_handle_callback_updates_task(db_session):
    """User action → updates participant status, flow_state, and card"""
    # Setup route and instance
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    instance = TaskInstance(
        handler_name="MockHandler",
        route_id=route.id,
        feishu_record_id="rec_1",
        platform="dingtalk",
        group_id="group_1",
        card_id="card_abc",
        status="pending",
        flow_state='{"step": 1}'
    )
    db_session.add(instance)
    db_session.flush()

    participant = TaskParticipant(
        task_id=instance.id,
        platform_user_id="user_1",
        feishu_user_id="f_user_1",
        role="participant",
        status="pending"
    )
    db_session.add(participant)
    db_session.commit()

    # Mock handler behavior
    mock_handler_instance = MagicMock()
    mock_handler_instance.handle_callback.return_value = TaskUpdate(
        status="confirmed",
        flow_state_update={"step": 2}
    )
    mock_handler_instance.build_card.return_value = CardData(
        title="Updated",
        sections=[],
        actions=[]
    )

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.update_group_card = AsyncMock()

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    result = await engine.handle_callback(
        platform="dingtalk",
        card_id="card_abc",
        user_id="user_1",
        action="confirm"
    )

    assert result is not None
    db_session.refresh(participant)
    assert participant.status == "confirmed"

    db_session.refresh(instance)
    assert instance.status == "confirmed"
    flow = json.loads(instance.flow_state)
    assert flow["step"] == 2
    assert "participant_progress" in flow

    mock_adapter.update_group_card.assert_called_once()


@pytest.mark.asyncio
async def test_handle_callback_returns_none_for_unknown_card(db_session):
    """Unknown card_id → returns None"""
    mock_registry = MagicMock()
    mock_adapter = MagicMock()

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    result = await engine.handle_callback(
        platform="dingtalk",
        card_id="card_unknown",
        user_id="user_1",
        action="confirm"
    )

    assert result is None


@pytest.mark.asyncio
async def test_handle_callback_with_flow_state_update(db_session):
    """Callback with flow_state_update → merges into existing flow_state"""
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    instance = TaskInstance(
        handler_name="MockHandler",
        route_id=route.id,
        feishu_record_id="rec_1",
        platform="dingtalk",
        group_id="group_1",
        card_id="card_abc",
        status="pending",
        flow_state='{"step": 1, "data": "old"}'
    )
    db_session.add(instance)
    db_session.flush()

    participant = TaskParticipant(
        task_id=instance.id,
        platform_user_id="user_1",
        feishu_user_id="f_user_1",
        role="participant",
        status="pending"
    )
    db_session.add(participant)
    db_session.commit()

    # Mock handler behavior - partial update
    mock_handler_instance = MagicMock()
    mock_handler_instance.handle_callback.return_value = TaskUpdate(
        status="confirmed",
        flow_state_update={"step": 2, "new_field": "value"}
    )
    mock_handler_instance.build_card.return_value = CardData(
        title="Updated",
        sections=[],
        actions=[]
    )

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.update_group_card = AsyncMock()

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    await engine.handle_callback(
        platform="dingtalk",
        card_id="card_abc",
        user_id="user_1",
        action="confirm"
    )

    db_session.refresh(instance)
    import json
    flow_state = json.loads(instance.flow_state)
    assert flow_state["step"] == 2
    assert flow_state["data"] == "old"
    assert flow_state["new_field"] == "value"
    assert "participant_progress" in flow_state


@pytest.mark.asyncio
async def test_dispatch_with_field_mapping(db_session):
    """Dispatch uses field_mapping from route"""
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping='{"title": "fields.name", "deadline": "fields.due_date"}',
        enabled=True
    )
    db_session.add(route)
    db_session.commit()

    mock_handler_instance = MagicMock()
    mock_handler_instance.parse_event.return_value = TaskData(
        title="Mapped Task",
        participants=["user_1"],
        deadline=None,
        parameters={}
    )
    mock_handler_instance.get_flow.return_value = FlowDefinition(
        states=["pending"],
        initial="pending"
    )
    mock_handler_instance.build_card.return_value = CardData(
        title="Card",
        sections=[],
        actions=[]
    )

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_123")

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    await engine.dispatch(
        table_id="tbl_test",
        record_id="rec_1",
        action="create",
        fields={"name": "Test Task", "due_date": "2026-12-31"}
    )

    # Verify handler was called with correct field_mapping
    import json
    expected_mapping = {"title": "fields.name", "deadline": "fields.due_date"}
    mock_handler_instance.parse_event.assert_called_once()
    call_args = mock_handler_instance.parse_event.call_args
    assert call_args[0][1] == expected_mapping


@pytest.mark.asyncio
async def test_dispatch_creates_task_with_deadline(db_session):
    """Task with deadline → stores deadline in instance"""
    from datetime import datetime, timezone

    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.commit()

    deadline = datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)

    mock_handler_instance = MagicMock()
    mock_handler_instance.parse_event.return_value = TaskData(
        title="Task with Deadline",
        participants=["user_1"],
        deadline=deadline,
        parameters={}
    )
    mock_handler_instance.get_flow.return_value = FlowDefinition(
        states=["pending"],
        initial="pending"
    )
    mock_handler_instance.build_card.return_value = CardData(
        title="Card",
        sections=[],
        actions=[]
    )

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_123")

    engine = TaskEngine(
        db=db_session,
        registry=mock_registry,
        adapters={"dingtalk": mock_adapter}
    )
    await engine.dispatch(
        table_id="tbl_test",
        record_id="rec_1",
        action="create",
        fields={}
    )

    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    # SQLite doesn't preserve timezone, compare without timezone
    assert instances[0].deadline.replace(tzinfo=timezone.utc) == deadline


@pytest.mark.asyncio
async def test_dispatch_stores_parameters_in_flow_state(db_session):
    """Dispatch stores task_data.parameters into flow_state"""
    route = TaskRoute(
        handler_name="MockHandler",
        feishu_table_id="tbl_test",
        platform="dingtalk",
        group_id="group_1",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.commit()

    mock_handler_instance = MagicMock()
    mock_handler_instance.parse_event.return_value = TaskData(
        title="Test",
        participants=["user_1"],
        deadline=None,
        parameters={"title": "样片拍摄", "deliverables": [{"name": "样片", "count": 3}]}
    )
    mock_handler_instance.get_flow.return_value = FlowDefinition(
        states=["pending"], initial="pending"
    )
    mock_handler_instance.build_card.return_value = CardData(title="Card", sections=[], actions=[])

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_123")

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})
    await engine.dispatch(table_id="tbl_test", record_id="rec_1", action="create", fields={})

    import json
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    flow = json.loads(instances[0].flow_state)
    assert flow["title"] == "样片拍摄"
    assert flow["deliverables"] == [{"name": "样片", "count": 3}]


@pytest.mark.asyncio
async def test_handle_callback_finds_participant_by_feishu_fallback(db_session):
    """If platform_user_id lookup fails, resolve via identity service"""
    from app.models.tables import UserMapping

    route = TaskRoute(
        handler_name="MockHandler", feishu_table_id="tbl_test",
        platform="dingtalk", group_id="group_1",
        field_mapping="{}", enabled=True
    )
    db_session.add(route)
    db_session.flush()

    instance = TaskInstance(
        handler_name="MockHandler", route_id=route.id,
        feishu_record_id="rec_1", platform="dingtalk",
        group_id="group_1", card_id="card_fb",
        status="pending", flow_state="{}"
    )
    db_session.add(instance)
    db_session.flush()

    participant = TaskParticipant(
        task_id=instance.id, feishu_user_id="f_user_1",
        platform_user_id=None, role="participant", status="pending"
    )
    db_session.add(participant)

    mapping = UserMapping(
        feishu_user_id="f_user_1", dingtalk_user_id="d_user_1",
        phone="13800138000", name="Test User"
    )
    db_session.add(mapping)
    db_session.commit()

    mock_handler_instance = MagicMock()
    mock_handler_instance.handle_callback.return_value = TaskUpdate(status="confirmed", flow_state_update=None)
    mock_handler_instance.build_card.return_value = CardData(title="Card", sections=[], actions=[])

    mock_handler_cls = MagicMock()
    mock_handler_cls.return_value = mock_handler_instance

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler_cls

    mock_adapter = MagicMock()
    mock_adapter.update_group_card = AsyncMock()

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})
    result = await engine.handle_callback(platform="dingtalk", card_id="card_fb", user_id="d_user_1", action="confirm")

    assert result is not None
    db_session.refresh(participant)
    assert participant.status == "confirmed"
