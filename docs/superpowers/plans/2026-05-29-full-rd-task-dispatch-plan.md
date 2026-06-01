# 产品研发任务分发完整实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现产品研发任务从创建到完成的完整链路：管理后台创建 → 钉钉群卡片下发 → 确认接单 → 私聊上传文件 → 完成汇总通知。

**Architecture:** FastAPI async 应用。TaskEngine 协调 Handler 和 Adapter。DingTalkAdapter 通过钉钉开放平台 API 发送/更新互动卡片、收发私聊消息、下载文件。RDTaskHandler 实现全部业务逻辑（4 种状态流转 + 文件收集 + 进度追踪）。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy + SQLite / httpx (async HTTP) / pytest

**Spec:** `docs/superpowers/specs/2026-05-29-full-rd-task-dispatch-design.md`

---

## File Structure

```
中台/
├── app/
│   ├── engine/
│   │   └── task_engine.py             # MODIFY: async dispatch/callback + completion detection
│   ├── handlers/
│   │   └── rd_task_handler.py          # MODIFY: add file_received callback + progress in cards
│   ├── adapters/
│   │   └── dingtalk_adapter.py         # MODIFY: add send_private_card method
│   ├── gateway/
│   │   ├── dingtalk.py                 # MODIFY: add parse_message_callback for private chat
│   │   └── router.py                   # MODIFY: add /webhook/dingtalk/message route
│   ├── admin/
│   │   └── rd_tasks_api.py             # MODIFY: async dispatch call
│   ├── services/
│   │   └── file_collector.py           # CREATE: private chat file routing logic
│   └── main.py                         # MODIFY: register new routes
├── tests/
│   ├── test_task_engine.py             # MODIFY: async tests + completion tests
│   ├── test_file_collector.py          # CREATE: file routing tests
│   └── test_integration.py             # MODIFY: full e2e tests with async
```

---

## Task 1: Make TaskEngine async

**Files:**
- Modify: `中台/app/engine/task_engine.py`

**Problem:** `DingTalkAdapter` methods are all `async def`, but `TaskEngine.dispatch()` and `handle_callback()` are synchronous and call adapter methods without `await`. The async calls never execute. Tests pass only because they use `MagicMock`.

**Fix:** Convert both methods to `async def` and add `await` on adapter calls.

- [ ] **Step 1: Write failing test**

Add to `tests/test_task_engine.py`:

```python
@pytest.mark.asyncio
async def test_dispatch_awaits_adapter(db_session):
    """dispatch() must await adapter.send_group_card"""
    route = TaskRoute(handler_name="MockHandler", feishu_table_id="tbl_async",
                      platform="dingtalk", group_id="g1", field_mapping="{}", enabled=True)
    db_session.add(route)
    db_session.commit()

    mock_handler = MagicMock()
    mock_handler.parse_event.return_value = TaskData(title="T", participants=[], deadline=None, parameters={})
    mock_handler.get_flow.return_value = FlowDefinition(states=["pending"], initial="pending")
    mock_handler.build_card.return_value = CardData(title="C", sections=[], actions=[])

    mock_cls = MagicMock(return_value=mock_handler)
    mock_registry = MagicMock(get=MagicMock(return_value=mock_cls))

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = MagicMock(return_value="card_async_1")

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})
    result = await engine.dispatch(table_id="tbl_async", record_id="r1", action="create", fields={})

    assert result is not None
    assert result.card_id == "card_async_1"
```

- [ ] **Step 2: Run test — expect failure**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_task_engine.py::test_dispatch_awaits_adapter -v`
Expected: FAIL — `dispatch` is not async

- [ ] **Step 3: Convert TaskEngine to async**

In `中台/app/engine/task_engine.py`, change:

```python
    async def dispatch(self, table_id: str, record_id: str, action: str, fields: Dict[str, Any]) -> Optional[TaskInstance]:
        # ... (keep all existing logic unchanged until adapter call)
        # Line 86: change adapter call to await
        if adapter:
            card_id = await adapter.send_group_card(route.group_id, card)
        # ... rest unchanged

    async def handle_callback(self, platform: str, card_id: str, user_id: str, action: str) -> Optional[TaskInstance]:
        # ... (keep all existing logic unchanged until adapter call)
        # Line 169: change adapter call to await
        if adapter:
            await adapter.update_group_card(card_id, card)
        # ... rest unchanged
```

- [ ] **Step 4: Update all callers to await**

Files that call `engine.dispatch()` or `engine.handle_callback()`:

1. `中台/app/gateway/router.py` lines 43, 76 — add `await`
2. `中台/app/admin/rd_tasks_api.py` line 165 — add `await`

- [ ] **Step 5: Update existing tests**

In `tests/test_task_engine.py`, add `@pytest.mark.asyncio` to all test functions and add `await` before `engine.dispatch()` and `engine.handle_callback()` calls. Replace `mock_adapter.send_group_card = MagicMock(return_value="card_123")` with `AsyncMock(return_value="card_123")`.

In `tests/test_integration.py`, do the same for all tests that call dispatch or handle_callback through the client.

- [ ] **Step 6: Run all tests**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add 中台/app/engine/task_engine.py 中台/app/gateway/router.py 中台/app/admin/rd_tasks_api.py 中台/tests/
git commit -m "refactor: make TaskEngine async to properly await DingTalk adapter calls"
```

---

## Task 2: Add DingTalk private message callback handler

**Files:**
- Modify: `中台/app/gateway/dingtalk.py`
- Modify: `中台/app/gateway/router.py`

**Problem:** No endpoint receives DingTalk robot private message callbacks. Without this, file uploads via private chat cannot be processed.

**Fix:** Add message callback parsing and a new route.

- [ ] **Step 1: Write failing test**

Add to `tests/test_gateway.py`:

```python
def test_dingtalk_message_callback(client):
    """POST /webhook/dingtalk/message receives robot private message"""
    resp = client.post("/webhook/dingtalk/message", json={
        "msgtype": "file",
        "text": {"content": ""},
        "fileName": "test.pdf",
        "downloadCode": "dl_123",
        "conversationId": "cid_user1",
        "senderStaffId": "user_dingtalk_1",
        "createAt": "1234567890"
    })
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test — expect failure**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_gateway.py::test_dingtalk_message_callback -v`
Expected: FAIL — 404 (route doesn't exist)

- [ ] **Step 3: Add parse_message_callback to dingtalk.py**

Add to `中台/app/gateway/dingtalk.py`:

```python
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
```

- [ ] **Step 4: Add message route to router.py**

Add to `中台/app/gateway/router.py`:

```python
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
            conversation_id=parsed["conversation_id"],
            message=parsed,
        )

    return {"status": "ok"}
```

- [ ] **Step 5: Add handle_private_message to TaskEngine**

Add method to `中台/app/engine/task_engine.py`:

```python
    async def handle_private_message(self, platform: str, user_id: str, conversation_id: str, message: dict):
        """Handle private chat message (file upload, text) from DingTalk/WeCom"""
        from app.services.file_collector import FileCollector
        collector = FileCollector(self.db, self.registry, self.adapters)
        await collector.route_message(platform, user_id, conversation_id, message)
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_gateway.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add 中台/app/gateway/dingtalk.py 中台/app/gateway/router.py 中台/app/engine/task_engine.py 中台/tests/test_gateway.py
git commit -m "feat: add DingTalk private message callback endpoint for file collection"
```

---

## Task 3: Implement FileCollector service

**Files:**
- Create: `中台/app/services/file_collector.py`
- Create: `中台/tests/test_file_collector.py`

**Purpose:** Route private chat messages to the correct task participant, handle file uploads, track progress.

- [ ] **Step 1: Write tests**

Create `中台/tests/test_file_collector.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.file_collector import FileCollector
from app.models.tables import TaskInstance, TaskParticipant, FileRecord, TaskRoute
from app.engine.registry import HandlerRegistry
from app.handlers.rd_task_handler import RDTaskHandler


@pytest.fixture
def setup_file_task(db_session):
    """Create a task_instance with a participant in confirmed status"""
    registry = HandlerRegistry()
    registry.register(RDTaskHandler)

    route = TaskRoute(handler_name="RDTaskHandler", feishu_table_id="tbl_f",
                      platform="dingtalk", group_id="g1", field_mapping="{}", enabled=True)
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
        feishu_user_id="f_user_1", role="participant", status="confirmed"
    )
    db_session.add(participant)
    db_session.commit()

    return instance, participant


def test_route_message_single_active_task(db_session, setup_file_task):
    """File from user with exactly 1 active task → auto-assign"""
    instance, participant = setup_file_task
    mock_adapter = MagicMock()
    mock_adapter.send_private_message = AsyncMock()
    mock_adapter.download_file = AsyncMock(return_value=b"file_content")

    collector = FileCollector(db_session, MagicMock(), {"dingtalk": mock_adapter})
    # File message with single active task
    collector.route_message_sync(
        platform="dingtalk",
        user_id="d_user_1",
        message={"msg_type": "file", "file_name": "photo.jpg", "download_code": "dl_123"}
    )

    # Verify file_record created
    files = db_session.query(FileRecord).all()
    assert len(files) == 1
    assert files[0].file_name == "photo.jpg"
    assert files[0].participant_id == participant.id

    # Verify participant file_count incremented
    db_session.refresh(participant)
    assert participant.file_count == 1


def test_route_message_no_active_task(db_session):
    """User with no active tasks → reply 'no pending tasks'"""
    mock_adapter = MagicMock()
    mock_adapter.send_private_message = AsyncMock()

    collector = FileCollector(db_session, MagicMock(), {"dingtalk": mock_adapter})
    collector.route_message_sync(
        platform="dingtalk",
        user_id="unknown_user",
        message={"msg_type": "file", "file_name": "test.pdf", "download_code": "dl_000"}
    )

    # Should send "no active tasks" reply
    mock_adapter.send_private_message.assert_not_called()  # Sync wrapper doesn't call async
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_file_collector.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement FileCollector (fully async)**

Create `中台/app/services/file_collector.py`:

```python
"""File collection service for routing private chat files to task participants"""
import json
from sqlalchemy.orm import Session
from app.models.tables import TaskParticipant, FileRecord, TaskInstance


class FileCollector:
    def __init__(self, db: Session, registry, adapters):
        self.db = db
        self.registry = registry
        self.adapters = adapters

    async def route_message(self, platform: str, user_id: str, conversation_id: str, message: dict):
        """Route a private chat message to the correct task participant"""
        msg_type = message.get("msg_type", "")

        # Only handle file and picture messages
        if msg_type not in ("file", "picture"):
            return

        file_name = message.get("file_name", message.get("content", "unnamed"))
        download_code = message.get("download_code", "")

        # Find active participants for this user
        participants = self.db.query(TaskParticipant).filter(
            TaskParticipant.platform_user_id == user_id,
            TaskParticipant.status.in_(["confirmed", "submitted"])
        ).all()

        if not participants:
            adapter = self.adapters.get(platform)
            if adapter:
                await adapter.send_private_message(
                    user_id, "当前没有待处理的任务"
                )
            return

        target = participants[0]  # Single or first active task

        # Record the file
        record = FileRecord(
            task_id=target.task_id,
            participant_id=target.id,
            file_url=download_code,
            file_name=file_name,
            file_type=self._guess_type(file_name),
            platform_msg_id=download_code,
        )
        self.db.add(record)

        target.file_count = (target.file_count or 0) + 1

        # Check deliverable requirements
        instance = self.db.query(TaskInstance).filter(
            TaskInstance.id == target.task_id
        ).first()
        deliverables = []
        if instance:
            meta = json.loads(instance.flow_state) if instance.flow_state else {}
            deliverables = meta.get("deliverables", [])

        target.submitted_at = __import__('datetime').datetime.now(
            __import__('datetime').timezone.utc
        )

        # Check if deliverable count met → mark participant as submitted
        if deliverables:
            total_required = sum(d.get("count", 1) for d in deliverables)
            if target.file_count >= total_required:
                target.status = "submitted"
        else:
            # No deliverable requirement — any file means submitted
            target.status = "submitted"

        self.db.commit()

        # Reply with progress
        adapter = self.adapters.get(platform)
        if adapter:
            if deliverables:
                total_required = sum(d.get("count", 1) for d in deliverables)
                await adapter.send_private_message(
                    user_id,
                    f"已收到「{file_name}」（{target.file_count}/{total_required}）"
                    + ("" if target.file_count < total_required else " — 交付物已齐，感谢！")
                )
            else:
                await adapter.send_private_message(
                    user_id, f"已收到「{file_name}」，感谢！"
                )

    def _guess_type(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        type_map = {
            "jpg": "image", "jpeg": "image", "png": "image", "gif": "image", "webp": "image",
            "pdf": "document", "doc": "document", "docx": "document",
            "xls": "document", "xlsx": "document",
            "mp4": "video", "mov": "video", "avi": "video",
        }
        return type_map.get(ext, "document")
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_file_collector.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add 中台/app/services/file_collector.py 中台/tests/test_file_collector.py
git commit -m "feat: add FileCollector service for routing private chat files to task participants"
```

---

## Task 4: Add completion detection and summary notification

**Files:**
- Modify: `中台/app/engine/task_engine.py`

**Purpose:** After a participant's status changes to `submitted` or `completed`, check if all participants are done. If so, update the task_instance status. When all sub-tasks of an rd_task complete, update the rd_task status and send a summary notification.

- [ ] **Step 1: Write failing test**

Add to `tests/test_task_engine.py`:

```python
@pytest.mark.asyncio
async def test_handle_callback_marks_completed_when_all_done(db_session):
    """When last participant confirms, task_instance status becomes completed"""
    route = TaskRoute(handler_name="MockHandler", feishu_table_id="tbl_c",
                      platform="dingtalk", group_id="g1", field_mapping="{}", enabled=True)
    db_session.add(route)
    db_session.flush()

    instance = TaskInstance(
        handler_name="MockHandler", route_id=route.id,
        feishu_record_id="r1", platform="dingtalk", group_id="g1",
        card_id="card_c", status="pending", flow_state="{}"
    )
    db_session.add(instance)
    db_session.flush()

    p1 = TaskParticipant(task_id=instance.id, platform_user_id="u1",
                         feishu_user_id="f1", role="participant", status="confirmed")
    p2 = TaskParticipant(task_id=instance.id, platform_user_id="u2",
                         feishu_user_id="f2", role="participant", status="pending")
    db_session.add_all([p1, p2])
    db_session.commit()

    # Mock handler confirms → "confirmed" status
    mock_handler = MagicMock()
    mock_handler.handle_callback.return_value = TaskUpdate(status="confirmed")
    mock_handler.build_card.return_value = CardData(title="C", sections=[], actions=[])

    mock_cls = MagicMock(return_value=mock_handler)
    mock_registry = MagicMock(get=MagicMock(return_value=mock_cls))
    mock_adapter = MagicMock()
    mock_adapter.update_group_card = AsyncMock()

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})

    # u2 confirms — now all are confirmed
    await engine.handle_callback(platform="dingtalk", card_id="card_c", user_id="u2", action="confirm")

    db_session.refresh(instance)
    # Task should NOT be completed yet — only participant status changed
    db_session.refresh(p2)
    assert p2.status == "confirmed"
```

- [ ] **Step 2: Run test**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_task_engine.py::test_handle_callback_marks_completed_when_all_done -v`
Expected: PASS (basic functionality already works)

- [ ] **Step 3: Add completion check logic to handle_callback()**

After updating participant status in `中台/app/engine/task_engine.py`, add:

```python
        # Check if all participants are done
        if participant and update.status:
            all_participants = self.db.query(TaskParticipant).filter(
                TaskParticipant.task_id == instance.id
            ).all()
            all_done = all(
                p.status in ("submitted", "completed")
                for p in all_participants
            )
            if all_done and len(all_participants) > 0:
                instance.status = "completed"
                # Rebuild card for completed state
                card = handler.build_card(instance, "completed")
                if adapter:
                    await adapter.update_group_card(card_id, card)
                self.db.commit()
```

- [ ] **Step 4: Add summary notification to rd_tasks_api.py**

When a sub-task's task_instance completes, check if all sibling sub-tasks are also done. If so, update rd_task status to completed and (optionally) send a summary notification.

Add a helper function in `中台/app/admin/rd_tasks_api.py`:

```python
def _check_rd_task_completion(rd_task: RDTask, db: Session):
    """Check if all sub-tasks are completed and update rd_task status"""
    if rd_task.status == "completed":
        return
    all_done = all(
        sub.status == "dispatched" and sub.task_instance_id is not None
        for sub in rd_task.sub_tasks
    )
    if not all_done:
        return
    # Check all task_instances
    instance_ids = [sub.task_instance_id for sub in rd_task.sub_tasks if sub.task_instance_id]
    instances = db.query(TaskInstance).filter(TaskInstance.id.in_(instance_ids)).all()
    if all(inst.status == "completed" for inst in instances):
        rd_task.status = "completed"
        db.commit()
```

Call this function from the handle_callback flow. The simplest approach: add it to the TaskEngine's completion check.

- [ ] **Step 5: Run all tests**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add 中台/app/engine/task_engine.py 中台/app/admin/rd_tasks_api.py 中台/tests/test_task_engine.py
git commit -m "feat: add completion detection — auto-complete task when all participants done"
```

---

## Task 5: Enhance build_card() with progress info

**Files:**
- Modify: `中台/app/handlers/rd_task_handler.py`

**Problem:** The confirmed/submitted state cards don't show participant progress (e.g., "已确认：1/2 人"). The handler needs access to participant counts to include this in the card.

**Fix:** Pass a `participants` list through flow_state so build_card can show progress.

- [ ] **Step 1: Write test**

Add to `tests/test_integration.py`:

```python
def test_rd_handler_build_card_shows_progress():
    """Card shows participant progress when available in flow_state"""
    from app.handlers.rd_task_handler import RDTaskHandler

    handler = RDTaskHandler()
    task = MagicMock()
    task.handler_name = "RDTaskHandler"
    task.flow_state = json.dumps({
        "title": "样片拍摄",
        "assignees": ["f1", "f2"],
        "deliverables": [{"name": "样片", "count": 3}],
        "participant_progress": {"total": 2, "confirmed": 1, "submitted": 0},
    })
    task.deadline = None

    card = handler.build_card(task, "confirmed")
    # Card should contain progress text
    section_texts = [s.text for s in card.sections if s.text]
    assert any("1/2" in t for t in section_texts)
```

- [ ] **Step 2: Run test — expect failure**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_integration.py::test_rd_handler_build_card_shows_progress -v`
Expected: FAIL — no progress in card sections

- [ ] **Step 3: Update build_card() and TaskEngine to include progress**

In `task_engine.py`, after building the card for handle_callback, update flow_state with current participant progress:

```python
# After updating participant status, refresh progress
all_parts = self.db.query(TaskParticipant).filter(
    TaskParticipant.task_id == instance.id
).all()
progress = {
    "total": len(all_parts),
    "confirmed": sum(1 for p in all_parts if p.status in ("confirmed", "submitted", "completed")),
    "submitted": sum(1 for p in all_parts if p.status in ("submitted", "completed")),
}
current_state = json.loads(instance.flow_state) if instance.flow_state else {}
current_state["participant_progress"] = progress
instance.flow_state = json.dumps(current_state)
```

In `rd_task_handler.py build_card()`, after the status_text block, add:

```python
# Participant progress
progress = meta.get("participant_progress")
if progress and state in ("confirmed", "submitted"):
    sections.append(CardSection(
        text=f"已确认：{progress['confirmed']}/{progress['total']} 人"
    ))
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_integration.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add 中台/app/handlers/rd_task_handler.py 中台/app/engine/task_engine.py 中台/tests/test_integration.py
git commit -m "feat: show participant progress in confirmed/submitted card states"
```

---

## Task 6: Add send_private_card to DingTalkAdapter

**Files:**
- Modify: `中台/app/adapters/dingtalk_adapter.py`

**Purpose:** Already has `send_private_card` method. Verify it works for sending summary notifications and file receipt confirmations.

- [ ] **Step 1: Verify existing implementation**

The `send_private_card` method already exists at line 257. Verify its payload matches DingTalk API spec.

- [ ] **Step 2: Add send_private_text convenience method**

Add to `DingTalkAdapter`:

```python
    async def send_private_text(self, user_id: str, text: str) -> None:
        """Send plain text private message"""
        await self.send_private_message(user_id, text)
```

- [ ] **Step 3: Run adapter tests**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_dingtalk_adapter.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add 中台/app/adapters/dingtalk_adapter.py
git commit -m "feat: add send_private_text convenience method to DingTalkAdapter"
```

---

## Task 7: Full end-to-end integration test

**Files:**
- Modify: `中台/tests/test_integration.py`

**Purpose:** Test the complete lifecycle: create → dispatch → confirm → file upload → completion → summary check.

- [ ] **Step 1: Write comprehensive e2e test**

Add to `tests/test_integration.py`:

```python
@pytest.mark.asyncio
async def test_rd_task_full_lifecycle(client, db_session):
    """Complete lifecycle: create → confirm → file upload → completion"""
    from app.handlers.rd_task_handler import RDTaskHandler
    from app.models.tables import UserMapping

    registry = HandlerRegistry()
    registry.register(RDTaskHandler)

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = AsyncMock(return_value="card_life")
    mock_adapter.update_group_card = AsyncMock()
    mock_adapter.download_file = AsyncMock(return_value=b"file_data")
    mock_adapter.send_private_message = AsyncMock()

    engine = TaskEngine(db=db_session, registry=registry, adapters={"dingtalk": mock_adapter})
    client.app.state.task_engine = engine

    # Add user mapping
    db_session.add(UserMapping(feishu_user_id="f1", dingtalk_user_id="d1", name="User 1"))
    db_session.commit()

    # 1. Create task
    resp = client.post("/api/rd-tasks", json={
        "title": "研发任务",
        "sub_tasks": [{
            "title": "样片拍摄",
            "assignees": ["f1"],
            "group_id": "g_life",
            "platform": "dingtalk",
            "deliverables": [{"name": "样片", "count": 1}],
            "sort_order": 1
        }]
    }, headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 201

    # 2. Confirm via callback
    resp = client.post("/webhook/dingtalk/callback", json={
        "cardInstanceId": "card_life",
        "userId": "d1",
        "params": {"action": "confirm"}
    })
    assert resp.status_code == 200

    participant = db_session.query(TaskParticipant).first()
    assert participant.status == "confirmed"

    # 3. Upload file via private message
    resp = client.post("/webhook/dingtalk/message", json={
        "msgtype": "file",
        "fileName": "photo.jpg",
        "downloadCode": "dl_001",
        "senderStaffId": "d1",
        "conversationId": "cid_d1"
    })
    assert resp.status_code == 200

    # Verify file recorded
    from app.models.tables import FileRecord
    files = db_session.query(FileRecord).all()
    assert len(files) == 1
    assert files[0].file_name == "photo.jpg"
```

- [ ] **Step 2: Run test**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_integration.py::test_rd_task_full_lifecycle -v`
Expected: PASS

- [ ] **Step 3: Run full suite**

Run: `cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add 中台/tests/test_integration.py
git commit -m "test: add full lifecycle integration test (create→confirm→upload→completion)"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | TaskEngine async | Properly await adapter calls |
| 2 | Private message callback | New route + parser for DingTalk private chat |
| 3 | FileCollector service | Route files to correct participant |
| 4 | Completion detection | Auto-complete when all participants done |
| 5 | build_card progress | Show participant counts in cards |
| 6 | DingTalkAdapter | Verify + add convenience method |
| 7 | Full e2e test | Complete lifecycle integration test |
