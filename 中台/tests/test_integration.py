"""End-to-end integration tests for the task dispatch middleware"""
import json
from unittest.mock import MagicMock, AsyncMock
from app.models.types import TaskData, CardData, CardSection, CardAction, FlowDefinition, RoleDefinition, TaskUpdate
from app.models.tables import TaskRoute, TaskInstance, TaskParticipant
from app.engine.handler_base import BaseHandler
from app.engine.registry import HandlerRegistry
from app.engine.task_engine import TaskEngine


class TestHandler(BaseHandler):
    """Test handler for integration tests"""
    handler_name = "TestHandler"

    def parse_event(self, event, field_mapping):
        """Parse event into task data"""
        return TaskData(
            title=event.get("fields", {}).get("title", "Test Task"),
            participants=["f_user_1"],
            deadline=None,
            parameters={}
        )

    def get_flow(self):
        """Return flow definition"""
        return FlowDefinition(states=["pending", "confirmed"], initial="pending")

    def get_roles(self):
        """Return role definition"""
        return RoleDefinition(roles=["creator", "participant"])

    def build_card(self, task, state):
        """Build card for task"""
        # task can be either TaskInstance or dict-like
        title = f"Task: {self.handler_name}"
        if hasattr(task, 'handler_name'):
            title = f"Task: {task.handler_name}"

        return CardData(
            title=title,
            sections=[CardSection(text=f"State: {state}")],
            actions=[CardAction(label="Confirm", action="confirm")]
        )

    def get_reminder_rules(self):
        """Return empty reminder rules"""
        return []

    def handle_callback(self, action, user, task):
        """Handle callback action"""
        return TaskUpdate(status="confirmed" if action == "confirm" else "unknown")


def setup_engine(db_session, registry):
    """Setup task engine with mocked adapters"""
    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_test_1")
    mock_adapter.update_group_card = AsyncMock(return_value=None)

    engine = TaskEngine(db=db_session, registry=registry, adapters={"dingtalk": mock_adapter})
    return engine, mock_adapter


def test_feishu_to_dingtalk_e2e(client, db_session):
    """End-to-end: Feishu webhook -> route lookup -> handler -> DingTalk adapter"""

    # 1. Setup: register handler, create engine
    registry = HandlerRegistry()
    registry.register(TestHandler)

    engine, mock_adapter = setup_engine(db_session, registry)
    client.app.state.task_engine = engine

    # 2. Create a route via admin API
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_e2e",
        "platform": "dingtalk",
        "group_id": "group_e2e",
        "field_mapping": {"title": "title_field"},
        "enabled": True
    }, headers={"Authorization": "Bearer changeme"})

    print(f"Create route response: {resp.status_code}")
    if resp.status_code != 201:
        print(f"Response body: {resp.json()}")
    assert resp.status_code == 201

    # 3. POST /webhook/feishu with event
    resp = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_e2e", "record_id": "rec_e2e_1", "action": "create"},
        "data": {"fields": {"title": "E2E Test Task"}}
    })
    assert resp.status_code == 200

    # 4. Assert task_instance created in DB
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    assert instances[0].handler_name == "TestHandler"
    assert instances[0].card_id == "card_test_1"
    assert instances[0].feishu_record_id == "rec_e2e_1"

    # 5. Assert DingTalk adapter.send_group_card was called
    mock_adapter.send_group_card.assert_called_once()
    call_args = mock_adapter.send_group_card.call_args
    assert call_args[0][0] == "group_e2e"  # group_id
    assert call_args[0][1].title == "Task: TestHandler"  # card title

    # 6. Assert task_participant rows created
    participants = db_session.query(TaskParticipant).all()
    assert len(participants) == 1
    assert participants[0].feishu_user_id == "f_user_1"
    assert participants[0].role == "participant"
    assert participants[0].status == "pending"


def test_dingtalk_callback_updates_task(client, db_session):
    """Test DingTalk callback updates task status"""

    # 1. Setup: register handler, create engine
    registry = HandlerRegistry()
    registry.register(TestHandler)

    engine, mock_adapter = setup_engine(db_session, registry)
    client.app.state.task_engine = engine

    # 2. Create task_instance + participant (simulating prior dispatch)
    route = TaskRoute(
        handler_name="TestHandler",
        feishu_table_id="tbl_e2e2",
        platform="dingtalk",
        group_id="group_e2e2",
        field_mapping=json.dumps({}),
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    instance = TaskInstance(
        handler_name="TestHandler",
        route_id=route.id,
        feishu_record_id="rec_e2e2",
        platform="dingtalk",
        group_id="group_e2e2",
        card_id="card_e2e2",
        status="pending",
        flow_state=json.dumps({})
    )
    db_session.add(instance)
    db_session.flush()

    participant = TaskParticipant(
        task_id=instance.id,
        platform_user_id="d_user_1",
        feishu_user_id="f_user_1",
        role="participant",
        status="pending"
    )
    db_session.add(participant)
    db_session.commit()

    # 3. POST /webhook/dingtalk/callback with card click
    resp = client.post("/webhook/dingtalk/callback", json={
        "cardInstanceId": "card_e2e2",
        "userId": "d_user_1",
        "params": {"action": "confirm"}
    })
    assert resp.status_code == 200

    # 4. Assert participant status updated
    db_session.refresh(participant)
    assert participant.status == "confirmed"

    # 5. Assert adapter.update_group_card was called
    mock_adapter.update_group_card.assert_called_once()
    call_args = mock_adapter.update_group_card.call_args
    assert call_args[0][0] == "card_e2e2"  # card_id

    # 6. Assert task instance status updated
    db_session.refresh(instance)
    assert instance.status == "confirmed"


def test_webhook_duplicate_detection(client, db_session):
    """Test that duplicate webhook events are properly handled"""

    # 1. Setup
    registry = HandlerRegistry()
    registry.register(TestHandler)

    engine, mock_adapter = setup_engine(db_session, registry)
    client.app.state.task_engine = engine

    # 2. Create a route
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_dup",
        "platform": "dingtalk",
        "group_id": "group_dup",
        "field_mapping": {},
        "enabled": True
    }, headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 201

    # 3. Send first webhook event
    resp = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_dup", "record_id": "rec_dup_1", "action": "create"},
        "data": {"fields": {"title": "Duplicate Test"}}
    })
    assert resp.status_code == 200

    # 4. Assert one task created
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1

    # 5. Send duplicate event (same table_id, record_id, action)
    resp = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_dup", "record_id": "rec_dup_1", "action": "create"},
        "data": {"fields": {"title": "Duplicate Test"}}
    })
    assert resp.status_code == 200

    # 6. Assert no new task created (duplicate detected)
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1  # Still only one task

    # 7. Assert adapter only called once
    assert mock_adapter.send_group_card.call_count == 1


def test_no_route_found(client, db_session):
    """Test behavior when no route is found for a webhook event"""

    # 1. Setup
    registry = HandlerRegistry()
    registry.register(TestHandler)

    engine, mock_adapter = setup_engine(db_session, registry)
    client.app.state.task_engine = engine

    # 2. Send webhook event for non-existent route
    resp = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_nonexistent", "record_id": "rec_123", "action": "create"},
        "data": {"fields": {"title": "No Route Test"}}
    })
    assert resp.status_code == 200  # Still returns 200 (graceful handling)

    # 3. Assert no task created
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 0

    # 4. Assert adapter not called
    mock_adapter.send_group_card.assert_not_called()


def test_disabled_route(client, db_session):
    """Test that disabled routes don't trigger task creation"""

    # 1. Setup
    registry = HandlerRegistry()
    registry.register(TestHandler)

    engine, mock_adapter = setup_engine(db_session, registry)
    client.app.state.task_engine = engine

    # 2. Create a disabled route
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_disabled",
        "platform": "dingtalk",
        "group_id": "group_disabled",
        "field_mapping": {},
        "enabled": False  # Disabled
    }, headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 201

    # 3. Send webhook event
    resp = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_disabled", "record_id": "rec_disabled", "action": "create"},
        "data": {"fields": {"title": "Disabled Route Test"}}
    })
    assert resp.status_code == 200

    # 4. Assert no task created
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 0

    # 5. Assert adapter not called
    mock_adapter.send_group_card.assert_not_called()


def test_url_verification_challenge(client):
    """Test Feishu URL verification challenge response"""

    # 1. Send URL verification challenge
    resp = client.post("/webhook/feishu", json={
        "challenge": "test_challenge_123",
        "token": "test_token"
    })
    assert resp.status_code == 200

    # 2. Assert challenge is echoed back
    data = resp.json()
    assert data["challenge"] == "test_challenge_123"


def test_multiple_participants(client, db_session):
    """Test task creation with multiple participants"""

    # 1. Setup: create handler with multiple participants
    class MultiParticipantHandler(TestHandler):
        handler_name = "MultiParticipantHandler"

        def parse_event(self, event, field_mapping):
            return TaskData(
                title="Multi Participant Task",
                participants=["f_user_1", "f_user_2", "f_user_3"],
                deadline=None,
                parameters={}
            )

    registry = HandlerRegistry()
    registry.register(MultiParticipantHandler)

    engine, mock_adapter = setup_engine(db_session, registry)
    client.app.state.task_engine = engine

    # 2. Create route
    resp = client.post("/api/routes", json={
        "handler_name": "MultiParticipantHandler",
        "feishu_table_id": "tbl_multi",
        "platform": "dingtalk",
        "group_id": "group_multi",
        "field_mapping": {},
        "enabled": True
    }, headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 201

    # 3. Send webhook event
    resp = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_multi", "record_id": "rec_multi", "action": "create"},
        "data": {"fields": {"title": "Multi Participant Task"}}
    })
    assert resp.status_code == 200

    # 4. Assert all participants created
    participants = db_session.query(TaskParticipant).all()
    assert len(participants) == 3

    participant_ids = {p.feishu_user_id for p in participants}
    assert participant_ids == {"f_user_1", "f_user_2", "f_user_3"}


def test_rd_handler_build_card_shows_correct_title():
    """build_card reads sub-task title from flow_state, not handler_name"""
    from app.handlers.rd_task_handler import RDTaskHandler
    from app.models.tables import TaskInstance

    handler = RDTaskHandler()
    task = MagicMock(spec=TaskInstance)
    task.handler_name = "RDTaskHandler"
    task.flow_state = json.dumps({
        "rd_sub_task_id": 1,
        "title": "样片拍摄",
        "assignees": ["f_user_1", "f_user_2"],
        "deliverables": [{"name": "样片", "type": "image", "count": 3}],
    })
    task.deadline = None

    card = handler.build_card(task, "pending")
    assert "样片拍摄" in card.title
    assert "RDTaskHandler" not in card.title
    assert len(card.actions) > 0
    assert card.actions[0].action == "confirm"


def test_rd_handler_build_card_confirmed_state():
    """Confirmed state card shows upload button"""
    from app.handlers.rd_task_handler import RDTaskHandler

    handler = RDTaskHandler()
    task = MagicMock()
    task.handler_name = "RDTaskHandler"
    task.flow_state = json.dumps({
        "title": "样片拍摄",
        "assignees": ["f_user_1", "f_user_2"],
        "deliverables": [{"name": "样片", "count": 3}],
    })
    task.deadline = None

    card = handler.build_card(task, "confirmed")
    assert any(a.action == "upload" for a in card.actions)


def test_rd_handler_build_card_completed_state():
    """Completed state card has no action buttons"""
    from app.handlers.rd_task_handler import RDTaskHandler

    handler = RDTaskHandler()
    task = MagicMock()
    task.handler_name = "RDTaskHandler"
    task.flow_state = json.dumps({
        "title": "样片拍摄",
        "deliverables": [{"name": "样片", "count": 3}],
    })
    task.deadline = None

    card = handler.build_card(task, "completed")
    assert len(card.actions) == 0


def test_rd_handler_handle_callback_tracks_flow_state():
    """handle_callback returns flow_state_update with action details"""
    from app.handlers.rd_task_handler import RDTaskHandler

    handler = RDTaskHandler()
    task = MagicMock()
    task.flow_state = json.dumps({"title": "样片拍摄"})

    update = handler.handle_callback("confirm", "user_1", task)
    assert update.status == "confirmed"
    assert update.flow_state_update is not None
    assert update.flow_state_update.get("confirmed_by") == "user_1"
    assert "confirmed_at" in update.flow_state_update


def test_rd_task_dispatch_e2e(client, db_session):
    """Full flow: create RD task via API -> dispatch -> DingTalk card sent"""
    from app.handlers.rd_task_handler import RDTaskHandler

    # 1. Register real RDTaskHandler
    registry = HandlerRegistry()
    registry.register(RDTaskHandler)

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_rd_1")
    mock_adapter.update_group_card = AsyncMock(return_value=None)

    engine = TaskEngine(db=db_session, registry=registry, adapters={"dingtalk": mock_adapter})
    client.app.state.task_engine = engine

    # 2. Create RD task via API
    resp = client.post("/api/rd-tasks", json={
        "title": "春季新品研发",
        "description": "2026年春季新品研发计划",
        "sub_tasks": [
            {
                "title": "样片拍摄",
                "description": "完成 3 组样片拍摄",
                "assignees": ["f_user_1", "f_user_2"],
                "group_id": "group_rd_1",
                "platform": "dingtalk",
                "deadline": "2026-12-31T00:00:00Z",
                "deliverables": [{"name": "样片", "type": "image", "count": 3}],
                "sort_order": 1
            }
        ]
    }, headers={"Authorization": "Bearer changeme"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "春季新品研发"
    assert len(data["sub_tasks"]) == 1
    assert data["sub_tasks"][0]["status"] == "dispatched"

    # 3. Verify task_instance created
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    assert instances[0].handler_name == "RDTaskHandler"
    assert instances[0].card_id == "card_rd_1"

    # 4. Verify card content passed to adapter
    mock_adapter.send_group_card.assert_called_once()
    card_arg = mock_adapter.send_group_card.call_args[0][1]
    assert "样片拍摄" in card_arg.title

    # 5. Verify participants created
    participants = db_session.query(TaskParticipant).all()
    assert len(participants) == 2
    feishu_ids = {p.feishu_user_id for p in participants}
    assert feishu_ids == {"f_user_1", "f_user_2"}


def test_rd_task_callback_e2e(client, db_session):
    """Full flow: dispatch -> DingTalk callback confirm -> status updated + card updated"""
    from app.handlers.rd_task_handler import RDTaskHandler
    from app.models.tables import UserMapping

    # 1. Register handler + setup engine
    registry = HandlerRegistry()
    registry.register(RDTaskHandler)

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_rd_cb")
    mock_adapter.update_group_card = AsyncMock(return_value=None)

    engine = TaskEngine(db=db_session, registry=registry, adapters={"dingtalk": mock_adapter})
    client.app.state.task_engine = engine

    # 2. Create RD task
    resp = client.post("/api/rd-tasks", json={
        "title": "研发任务",
        "sub_tasks": [{
            "title": "子任务A",
            "assignees": ["f_user_1"],
            "group_id": "group_cb",
            "platform": "dingtalk",
            "sort_order": 1
        }]
    }, headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 201

    # 3. Add user mapping so callback can resolve participant
    mapping = UserMapping(feishu_user_id="f_user_1", dingtalk_user_id="d_user_1", name="User 1")
    db_session.add(mapping)
    db_session.commit()

    # 4. Simulate DingTalk callback
    resp = client.post("/webhook/dingtalk/callback", json={
        "cardInstanceId": "card_rd_cb",
        "userId": "d_user_1",
        "params": {"action": "confirm"}
    })
    assert resp.status_code == 200

    # 5. Verify participant status updated
    participant = db_session.query(TaskParticipant).filter(
        TaskParticipant.feishu_user_id == "f_user_1"
    ).first()
    assert participant.status == "confirmed"

    # 6. Verify card updated via adapter
    mock_adapter.update_group_card.assert_called_once()
