# E2E Pipeline Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 specific gaps to make the "RD task create → DingTalk card dispatch → user confirm callback" pipeline run end-to-end.

**Architecture:** The core TaskEngine + DingTalkAdapter + RDTaskHandler are already implemented. Fixes target: (1) storing sub-task metadata in flow_state during dispatch so build_card() can render accurate content, (2) tracking state transitions in flow_state during callbacks, (3) improving participant lookup robustness, and (4) integration testing the real RDTaskHandler flow.

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy + SQLite / pytest

**Spec:** `docs/superpowers/specs/2026-05-29-e2e-pipeline-fixes-design.md`

---

## File Structure

```
中台/
├── app/
│   ├── engine/task_engine.py           # MODIFY: enrich flow_state in dispatch(), improve participant lookup
│   ├── handlers/rd_task_handler.py     # MODIFY: fix build_card() content, fix handle_callback() flow_state
│   └── services/identity.py           # NO CHANGE (already sufficient)
├── tests/
│   └── test_integration.py             # MODIFY: add RDTaskHandler dispatch + callback integration tests
```

---

## Task 1: Enrich flow_state in TaskEngine.dispatch()

**Files:**
- Modify: `中台/app/engine/task_engine.py` lines 53-75 (dispatch method)

**Problem:** When dispatch creates a task_instance, the flow_state is `json.dumps({})` — empty. The handler's parse_event() returns a `TaskData` with `parameters` dict that contains sub-task metadata (title, deliverables, assignees), but this data is never stored in flow_state. Without it, build_card() cannot render accurate card content.

**Fix:** Store `task_data.parameters` into `flow_state` during dispatch so handlers can read it later.

- [ ] **Step 1: Write failing test**

Add to `中台/tests/test_task_engine.py`:

```python
def test_dispatch_stores_parameters_in_flow_state(db_session):
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
    mock_adapter.send_group_card.return_value = "card_123"

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})
    engine.dispatch(table_id="tbl_test", record_id="rec_1", action="create", fields={})

    import json
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    flow = json.loads(instances[0].flow_state)
    assert flow["title"] == "样片拍摄"
    assert flow["deliverables"] == [{"name": "样片", "count": 3}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 中台 && python -m pytest tests/test_task_engine.py::test_dispatch_stores_parameters_in_flow_state -v`
Expected: FAIL — flow_state is `{}`, parameters not stored.

- [ ] **Step 3: Modify task_engine.py dispatch() to store parameters in flow_state**

In `中台/app/engine/task_engine.py`, change line 73-74 from:
```python
flow_state=json.dumps({}),
```
to:
```python
flow_state=json.dumps(task_data.parameters or {}),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd 中台 && python -m pytest tests/test_task_engine.py::test_dispatch_stores_parameters_in_flow_state -v`
Expected: PASS

- [ ] **Step 5: Run existing tests to ensure no regression**

Run: `cd 中台 && python -m pytest tests/test_task_engine.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add 中台/app/engine/task_engine.py 中台/tests/test_task_engine.py
git commit -m "fix(task-engine): store task_data.parameters in flow_state during dispatch"
```

---

## Task 2: Fix RDTaskHandler.build_card() card content

**Files:**
- Modify: `中台/app/handlers/rd_task_handler.py` lines 30-60 (build_card method)

**Problem:** build_card() uses `task.handler_name` as card title (shows "子任务：RDTaskHandler" instead of the actual title like "子任务：样片拍摄"). Also, deliverables are read from flow_state but the data structure doesn't match what dispatch stores. State-dependent content is minimal.

**Fix:** Read sub-task metadata from flow_state (stored by Task 1). Build accurate cards for each state with proper title, deadline, deliverables, and assignees.

- [ ] **Step 1: Write failing test**

Add to `中台/tests/test_integration.py`:

```python
class RDTaskHandlerTestWrapper(BaseHandler):
    """Thin wrapper to test RDTaskHandler in isolation"""
    handler_name = "RDTaskHandlerTest"

    def parse_event(self, event, field_mapping):
        from app.handlers.rd_task_handler import RDTaskHandler
        return RDTaskHandler().parse_event(event, field_mapping)

    def get_flow(self):
        from app.handlers.rd_task_handler import RDTaskHandler
        return RDTaskHandler().get_flow()

    def get_roles(self):
        from app.handlers.rd_task_handler import RDTaskHandler
        return RDTaskHandler().get_roles()

    def build_card(self, task, state):
        from app.handlers.rd_task_handler import RDTaskHandler
        return RDTaskHandler().build_card(task, state)

    def get_reminder_rules(self):
        return []

    def handle_callback(self, action, user, task):
        from app.handlers.rd_task_handler import RDTaskHandler
        return RDTaskHandler().handle_callback(action, user, task)


def test_rd_handler_build_card_shows_correct_title():
    """build_card reads sub-task title from flow_state, not handler_name"""
    from app.handlers.rd_task_handler import RDTaskHandler
    from app.models.tables import TaskInstance

    handler = RDTaskHandler()

    # Simulate a task_instance with flow_state containing sub-task metadata
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
    """Confirmed state card shows progress and upload button"""
    from app.handlers.rd_task_handler import RDTaskHandler

    handler = RDTaskHandler()

    task = MagicMock(spec=TaskInstance)
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

    task = MagicMock(spec=TaskInstance)
    task.handler_name = "RDTaskHandler"
    task.flow_state = json.dumps({
        "title": "样片拍摄",
        "deliverables": [{"name": "样片", "count": 3}],
    })
    task.deadline = None

    card = handler.build_card(task, "completed")
    assert len(card.actions) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 中台 && python -m pytest tests/test_integration.py::test_rd_handler_build_card_shows_correct_title -v`
Expected: FAIL — card title shows "子任务：RDTaskHandler"

- [ ] **Step 3: Rewrite build_card() in RDTaskHandler**

Replace the entire `build_card` method in `中台/app/handlers/rd_task_handler.py` with:

```python
def build_card(self, task, state):
    # Read sub-task metadata from flow_state (stored by TaskEngine.dispatch)
    meta = {}
    if isinstance(task.flow_state, str):
        try:
            meta = json.loads(task.flow_state)
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(task.flow_state, dict):
        meta = task.flow_state

    title = meta.get("title", "研发子任务")
    deliverables = meta.get("deliverables", [])
    assignees = meta.get("assignees", [])

    sections = []

    # Deadline
    if task.deadline:
        sections.append(CardSection(text=f"截止时间：{task.deadline.strftime('%Y-%m-%d')}"))

    # Deliverables
    if deliverables:
        items = [f"{d.get('name', '?')} × {d.get('count', 1)}" for d in deliverables]
        sections.append(CardSection(text=f"交付物：{', '.join(items)}"))

    # Assignees
    if assignees:
        sections.append(CardSection(text=f"负责人：{', '.join(assignees)}"))

    # Status indicator for non-pending states
    status_text = {"confirmed": "已确认 ✓", "submitted": "已提交 ✓✓", "completed": "已完成 ✓✓"}
    if state in status_text:
        sections.insert(0, CardSection(text=status_text[state]))

    # Actions by state
    actions = []
    if state == "pending":
        actions.append(CardAction(label="确认接单", action="confirm", style="primary"))
    elif state == "confirmed":
        actions.append(CardAction(label="上传文件", action="upload"))

    return CardData(
        title=f"子任务：{title}",
        sections=sections,
        actions=actions,
    )
```

- [ ] **Step 4: Run tests**

Run: `cd 中台 && python -m pytest tests/test_integration.py::test_rd_handler_build_card -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add 中台/app/handlers/rd_task_handler.py 中台/tests/test_integration.py
git commit -m "fix(rd-handler): build_card reads title from flow_state, shows accurate content per state"
```

---

## Task 3: Fix RDTaskHandler.handle_callback() flow_state tracking

**Files:**
- Modify: `中台/app/handlers/rd_task_handler.py` lines 67-69 (handle_callback method)

**Problem:** handle_callback() returns only a new status string. It doesn't track when/who performed the action in flow_state, making it impossible to audit state transitions.

**Fix:** Return flow_state_update dict with action details and timestamp.

- [ ] **Step 1: Write failing test**

Add to `中台/tests/test_integration.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 中台 && python -m pytest tests/test_integration.py::test_rd_handler_handle_callback_tracks_flow_state -v`
Expected: FAIL — `flow_state_update` is None

- [ ] **Step 3: Fix handle_callback()**

Replace handle_callback() in `中台/app/handlers/rd_task_handler.py`:

```python
def handle_callback(self, action, user, task):
    from datetime import datetime, timezone

    status_map = {"confirm": "confirmed", "upload": "submitted"}
    new_status = status_map.get(action)

    flow_update = None
    if new_status:
        flow_update = {
            f"{new_status}_by": user,
            f"{new_status}_at": datetime.now(timezone.utc).isoformat(),
        }

    return TaskUpdate(status=new_status, flow_state_update=flow_update)
```

- [ ] **Step 4: Run test**

Run: `cd 中台 && python -m pytest tests/test_integration.py::test_rd_handler_handle_callback_tracks_flow_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add 中台/app/handlers/rd_task_handler.py 中台/tests/test_integration.py
git commit -m "fix(rd-handler): track action details and timestamps in flow_state on callback"
```

---

## Task 4: Improve participant lookup in TaskEngine.handle_callback()

**Files:**
- Modify: `中台/app/engine/task_engine.py` lines 131-135 (handle_callback participant lookup)

**Problem:** handle_callback() searches for participant by `platform_user_id`, but participants are created with `platform_user_id=None` (identity mapping hasn't resolved them yet). This means callbacks from DingTalk won't find the participant, and the status update silently fails.

**Fix:** Add fallback lookup by feishu_user_id via IdentityService. If direct platform_user_id lookup fails, resolve the platform user ID to feishu user ID and try again.

- [ ] **Step 1: Write failing test**

Add to `中台/tests/test_task_engine.py`:

```python
def test_handle_callback_finds_participant_by_feishu_fallback(db_session):
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

    # Participant has no platform_user_id (not yet resolved)
    participant = TaskParticipant(
        task_id=instance.id, feishu_user_id="f_user_1",
        platform_user_id=None, role="participant", status="pending"
    )
    db_session.add(participant)

    # User mapping exists: f_user_1 → d_user_1
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

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})
    result = engine.handle_callback(platform="dingtalk", card_id="card_fb", user_id="d_user_1", action="confirm")

    assert result is not None
    db_session.refresh(participant)
    assert participant.status == "confirmed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd 中台 && python -m pytest tests/test_task_engine.py::test_handle_callback_finds_participant_by_feishu_fallback -v`
Expected: FAIL — participant not found because platform_user_id is None

- [ ] **Step 3: Modify handle_callback() in task_engine.py**

Replace lines 130-135 in `中台/app/engine/task_engine.py`:

```python
        # 3. Resolve participant: try platform_user_id first, then feishu_user_id fallback
        participant = self.db.query(TaskParticipant).filter(
            TaskParticipant.task_id == instance.id,
            TaskParticipant.platform_user_id == user_id
        ).first()

        if not participant:
            # Fallback: resolve platform user ID → feishu user ID via identity service
            from app.services.identity import IdentityService
            identity = IdentityService(self.db)
            feishu_uid = identity.get_feishu_user_id(user_id, platform)
            if feishu_uid:
                participant = self.db.query(TaskParticipant).filter(
                    TaskParticipant.task_id == instance.id,
                    TaskParticipant.feishu_user_id == feishu_uid
                ).first()
```

- [ ] **Step 4: Run test**

Run: `cd 中台 && python -m pytest tests/test_task_engine.py::test_handle_callback_finds_participant_by_feishu_fallback -v`
Expected: PASS

- [ ] **Step 5: Run all task_engine tests**

Run: `cd 中台 && python -m pytest tests/test_task_engine.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add 中台/app/engine/task_engine.py 中台/tests/test_task_engine.py
git commit -m "fix(task-engine): fallback participant lookup via identity service when platform_user_id is unresolved"
```

---

## Task 5: Add RDTaskHandler end-to-end integration test

**Files:**
- Modify: `中台/tests/test_integration.py` (add new tests)

**Problem:** Existing integration tests use a generic TestHandler. No test exercises the real RDTaskHandler through the full pipeline: rd-task create → route creation → dispatch → DingTalk card send → callback → card update.

**Fix:** Add integration tests that use the real RDTaskHandler and exercise the full rd-task lifecycle.

- [ ] **Step 1: Write integration test**

Add to `中台/tests/test_integration.py`:

```python
def test_rd_task_dispatch_e2e(client, db_session):
    """Full flow: create RD task → dispatch → DingTalk card sent"""
    from app.handlers.rd_task_handler import RDTaskHandler

    # 1. Register real RDTaskHandler
    registry = HandlerRegistry()
    registry.register(RDTaskHandler)

    mock_adapter = MagicMock()
    mock_adapter.send_group_card.return_value = "card_rd_1"
    mock_adapter.update_group_card.return_value = None

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
    """Full flow: dispatch → callback confirm → status updated + card updated"""
    from app.handlers.rd_task_handler import RDTaskHandler
    from app.models.tables import UserMapping

    # 1. Register handler + setup engine
    registry = HandlerRegistry()
    registry.register(RDTaskHandler)

    mock_adapter = MagicMock()
    mock_adapter.send_group_card.return_value = "card_rd_cb"
    mock_adapter.update_group_card.return_value = None

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
```

- [ ] **Step 2: Run tests**

Run: `cd 中台 && python -m pytest tests/test_integration.py::test_rd_task_dispatch_e2e tests/test_integration.py::test_rd_task_callback_e2e -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd 中台 && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add 中台/tests/test_integration.py
git commit -m "test: add RDTaskHandler end-to-end dispatch and callback integration tests"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | TaskEngine.dispatch() | Store task_data.parameters in flow_state |
| 2 | RDTaskHandler.build_card() | Read title/metadata from flow_state, accurate state-dependent cards |
| 3 | RDTaskHandler.handle_callback() | Track action details and timestamps in flow_state |
| 4 | TaskEngine.handle_callback() | Fallback participant lookup via IdentityService |
| 5 | Integration tests | RDTaskHandler e2e dispatch + callback tests |
