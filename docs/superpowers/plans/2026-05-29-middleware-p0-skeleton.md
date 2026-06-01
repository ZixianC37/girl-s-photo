# 业务中台基座 P0 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建业务中台的最小可运行骨架——能接收飞书 webhook 事件，通过路由表找到对应 Handler，调用钉钉适配器发送消息。

**Architecture:** 插件式 TaskHandler 引擎 + 消息适配器层。FastAPI 接收 webhook，事件网关验签去重路由，TaskEngine 调用 Handler 解析事件并构建卡片，适配器翻译为平台 API 调用。SQLite 存运行时数据。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy + SQLite / pytest / httpx (test client)

**Spec:** `docs/superpowers/specs/2026-05-29-business-middleware-platform-design.md`

---

## File Structure

```
middleware/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, mount routes
│   ├── config.py                  # Settings from env vars (pydantic-settings)
│   ├── database.py                # SQLite engine + session + init_db()
│   ├── models/
│   │   ├── __init__.py
│   │   ├── types.py               # Dataclasses: TaskData, CardData, etc.
│   │   ├── tables.py              # SQLAlchemy ORM models (6 tables)
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── router.py              # /webhook/feishu, /webhook/dingtalk routes
│   │   ├── feishu.py              # Feishu webhook verification + parsing
│   │   ├── dingtalk.py            # DingTalk callback verification + parsing
│   │   ├── dedup.py               # Event deduplication (in-memory set + TTL)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── handler_base.py        # TaskHandler ABC + BaseHandler
│   │   ├── registry.py            # Handler auto-discovery from handlers/ dir
│   │   ├── task_engine.py         # Core: receive event → route → dispatch
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                # MessageAdapter ABC
│   │   ├── dingtalk_adapter.py    # DingTalk API client (cards + messages)
│   │   ├── wecom_adapter.py       # WeCom stub (NotImplementedError)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── identity.py            # User mapping service
│   │   ├── message_queue.py       # Rate-limited async queue
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── routes_api.py          # CRUD for task_route + handler listing
│   │   ├── auth.py                # Bearer token auth dependency
│   ├── handlers/                  # Handler plugins (empty in P0)
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures: test DB, test client, mock adapter
│   ├── test_types.py              # Type construction and validation
│   ├── test_handler_registry.py   # Handler discovery and validation
│   ├── test_gateway.py            # Webhook endpoint tests
│   ├── test_task_engine.py        # Routing + dispatch logic
│   ├── test_identity.py           # User mapping logic
│   ├── test_message_queue.py      # Rate limiting
│   ├── test_admin_api.py          # Route CRUD + handler listing
│   ├── test_dingtalk_adapter.py   # Adapter API call construction
│   └── test_integration.py        # End-to-end: Feishu webhook → DingTalk send
├── requirements.txt
├── Dockerfile
├── .env.example
```

---

## Task 1: Project scaffolding + config

**Files:**
- Create: `middleware/requirements.txt`
- Create: `middleware/.env.example`
- Create: `middleware/app/__init__.py`
- Create: `middleware/app/config.py`
- Create: `middleware/app/main.py`
- Test: `middleware/tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.111
uvicorn[standard]>=0.29
sqlalchemy>=2.0
pydantic-settings>=2.2
httpx>=0.27
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 2: Create .env.example**

```
# Feishu
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=

# DingTalk
DINGTALK_APP_KEY=
DINGTALK_APP_SECRET=
DINGTALK_ROBOT_CODE=

# WeCom (P2)
WECOM_CORP_ID=
WECOM_AGENT_ID=
WECOM_SECRET=

# Admin
ADMIN_TOKEN=changeme

# Database
DATABASE_URL=sqlite:///./middleware.db
```

- [ ] **Step 3: Create config.py with pydantic-settings**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    dingtalk_app_key: str = ""
    dingtalk_app_secret: str = ""
    dingtalk_robot_code: str = ""
    wecom_corp_id: str = ""
    wecom_agent_id: str = ""
    wecom_secret: str = ""
    admin_token: str = "changeme"
    database_url: str = "sqlite:///./middleware.db"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: Create main.py with FastAPI app + lifespan**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import init_db, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    yield

app = FastAPI(title="Business Middleware", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Create conftest.py with test fixtures**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, init_db
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_engine():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 6: Install deps and verify**

Run: `cd middleware && pip install -r requirements.txt && python -c "from app.config import settings; print('OK')"`

- [ ] **Step 7: Run health check test**

Run: `cd middleware && python -m pytest tests/ -v -k "not test_" --co` (collect only, verify imports work)

- [ ] **Step 8: Commit**

```bash
git add middleware/
git commit -m "feat(middleware): project scaffolding with FastAPI + config"
```

---

## Task 2: Database models (6 tables)

**Files:**
- Create: `middleware/app/database.py`
- Create: `middleware/app/models/__init__.py`
- Create: `middleware/app/models/tables.py`
- Test: `middleware/tests/test_types.py`

- [ ] **Step 1: Write failing test for table creation**

```python
# tests/test_types.py
from sqlalchemy import inspect

def test_tables_created(db_engine):
    table_names = inspect(db_engine).get_table_names()
    assert "task_route" in table_names
    assert "task_instance" in table_names
    assert "task_participant" in table_names
    assert "file_record" in table_names
    assert "reminder_log" in table_names
    assert "user_mapping" in table_names
```

- [ ] **Step 2: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(target_engine=None):
    Base.metadata.create_all(target_engine or engine)
```

Note: `tables.py` imports `Base` from `database.py`. All ORM models inherit from this shared `Base`. Tests use in-memory SQLite and call `init_db(test_engine)`.

- [ ] **Step 3: Create tables.py with all 6 ORM models**

Define TaskRoute, TaskInstance, TaskParticipant, FileRecord, ReminderLog, UserMapping per spec schema. Use SQLAlchemy `mapped_column`. Import `Base` from `app.database`. JSONB fields use `Text` type for SQLite compatibility.

- [ ] **Step 4: Run test to verify tables created**

Run: `cd middleware && python -m pytest tests/test_types.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add middleware/app/database.py middleware/app/models/
git commit -m "feat(middleware): database models for 6 tables"
```

---

## Task 3: Core types (TaskData, CardData, etc.)

**Files:**
- Create: `middleware/app/models/types.py`
- Test: `middleware/tests/test_types.py` (extend)

- [ ] **Step 1: Write failing test for type construction**

```python
# Add to tests/test_types.py
from app.models.types import TaskData, CardData, CardSection, CardAction

def test_task_data_construction():
    td = TaskData(title="Test Task", participants=["u1", "u2"], deadline=None, parameters={"key": "val"})
    assert td.title == "Test Task"
    assert len(td.participants) == 2

def test_card_data_construction():
    card = CardData(
        title="Card Title",
        subtitle="sub",
        sections=[CardSection(text="hello", fields=[{"k": "v"}])],
        actions=[CardAction(label="Click", action="confirm")]
    )
    assert card.actions[0].action == "confirm"
```

- [ ] **Step 2: Create types.py with all dataclasses from spec**

Copy all dataclass definitions from spec: TaskData, CardData, CardSection, CardAction, TaskUpdate, FlowDefinition, RoleDefinition, ReminderRule.

- [ ] **Step 3: Run tests**

Run: `cd middleware && python -m pytest tests/test_types.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add middleware/app/models/types.py
git commit -m "feat(middleware): core type definitions for Handler interface"
```

---

## Task 4: BaseHandler + registry

**Files:**
- Create: `middleware/app/engine/__init__.py`
- Create: `middleware/app/engine/handler_base.py`
- Create: `middleware/app/engine/registry.py`
- Create: `middleware/app/handlers/__init__.py`
- Test: `middleware/tests/test_handler_registry.py`

- [ ] **Step 1: Write failing test for handler registration**

```python
# tests/test_handler_registry.py
import pytest
from app.engine.registry import HandlerRegistry

def test_registry_empty_initially():
    reg = HandlerRegistry()
    assert reg.list_handlers() == []

def test_registry_registers_handler():
    from app.engine.handler_base import BaseHandler
    class TestHandler(BaseHandler):
        def parse_event(self, event, field_mapping): ...
        def get_flow(self): ...
        def get_roles(self): ...
        def build_card(self, task, state): ...
        def get_reminder_rules(self): ...
        def handle_callback(self, action, user, task): ...

    reg = HandlerRegistry()
    reg.register(TestHandler)
    assert "TestHandler" in reg.list_handlers()

def test_registry_rejects_duplicate():
    # Same handler registered twice raises ValueError
    ...

def test_registry_get_handler():
    # registry.get("TestHandler") returns the class
    ...
```

- [ ] **Step 2: Create handler_base.py**

Define `TaskHandler` ABC with 6 abstract methods and `BaseHandler` with `handler_name` class attribute auto-set from class name, plus `validate()` classmethod.

- [ ] **Step 3: Create registry.py**

`HandlerRegistry` class with `register(cls)`, `get(name)`, `list_handlers()`, `auto_discover(handlers_dir)` methods. `auto_discover` scans the `handlers/` directory for Python files, imports them, finds `BaseHandler` subclasses, registers them. Validates no duplicate names.

- [ ] **Step 4: Run tests**

Run: `cd middleware && python -m pytest tests/test_handler_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add middleware/app/engine/ middleware/app/handlers/
git commit -m "feat(middleware): BaseHandler interface + auto-discovery registry"
```

---

## Task 5: Task engine

**Files:**
- Create: `middleware/app/engine/task_engine.py`
- Test: `middleware/tests/test_task_engine.py`

- [ ] **Step 1: Write failing test for event dispatch**

```python
# tests/test_task_engine.py
from app.engine.task_engine import TaskEngine
from unittest.mock import MagicMock

def test_dispatch_creates_task_instance(db_session):
    """Event for known route → creates task_instance + calls handler"""
    from app.models.tables import TaskRoute
    route = TaskRoute(handler_name="MockHandler", feishu_table_id="tbl_test",
                      platform="dingtalk", group_id="group_1",
                      field_mapping={}, enabled=True)
    db_session.add(route)
    db_session.commit()

    mock_handler = MagicMock()
    mock_handler.parse_event.return_value = MagicMock(title="Test", participants=[], deadline=None, parameters={})
    mock_handler.get_flow.return_value = MagicMock(states=["pending"], initial="pending")
    mock_handler.build_card.return_value = MagicMock(title="Card", sections=[], actions=[])

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_handler

    mock_adapter = MagicMock()
    mock_adapter.send_group_card = MagicMock(return_value="card_123")

    engine = TaskEngine(db=db_session, registry=mock_registry, adapters={"dingtalk": mock_adapter})
    engine.dispatch(table_id="tbl_test", record_id="rec_1", action="create", fields={})

    from app.models.tables import TaskInstance
    instances = db_session.query(TaskInstance).all()
    assert len(instances) == 1
    assert instances[0].handler_name == "MockHandler"
    assert instances[0].card_id == "card_123"
```

- [ ] **Step 2: Create task_engine.py**

```python
class TaskEngine:
    def __init__(self, db, registry, adapters): ...

    def dispatch(self, table_id, record_id, action, fields):
        """Core dispatch: route → handler → adapter"""
        # 1. Query task_route WHERE feishu_table_id = table_id AND enabled
        # 2. Get handler from registry
        # 3. handler.parse_event(event, route.field_mapping)
        # 4. Create task_instance row(s) (one per platform)
        # 5. handler.build_card(task, initial_state)
        # 6. adapter.send_group_card(route.group_id, card)
        # 7. Update task_instance.card_id
        # 8. Create task_participant rows (identity mapping)

    def handle_callback(self, platform, card_id, user_id, action):
        """Handle user interaction from DingTalk/WeCom"""
        # 1. Query task_instance by card_id
        # 2. Get handler
        # 3. handler.handle_callback(action, user, task)
        # 4. Update task_participant status
        # 5. Merge flow_state_update
        # 6. handler.build_card for updated state
        # 7. adapter.update_group_card
```

Note: P0 uses synchronous methods. Async wrappers added in P1 when integrating with real platform APIs.

- [ ] **Step 3: Run tests**

Run: `cd middleware && python -m pytest tests/test_task_engine.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add middleware/app/engine/task_engine.py
git commit -m "feat(middleware): task engine with dispatch + callback handling"
```

---

## Task 6: DingTalk adapter

**Files:**
- Create: `middleware/app/adapters/__init__.py`
- Create: `middleware/app/adapters/base.py`
- Create: `middleware/app/adapters/dingtalk_adapter.py`
- Create: `middleware/app/adapters/wecom_adapter.py`
- Test: `middleware/tests/test_dingtalk_adapter.py`

- [ ] **Step 1: Write failing test for adapter send**

```python
# tests/test_dingtalk_adapter.py
from unittest.mock import AsyncMock, patch

async def test_send_group_card_calls_api():
    adapter = DingTalkAdapter(app_key="k", app_secret="s", robot_code="r")
    card = CardData(title="T", sections=[], actions=[])

    with patch.object(adapter, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"cardBizId": "card_1"}
        card_id = await adapter.send_group_card("group_1", card)
        assert card_id == "card_1"
        mock_req.assert_called_once()
```

- [ ] **Step 2: Create base.py with MessageAdapter ABC**

6 abstract methods: send_group_card, update_group_card, send_private_message, send_private_card, download_file, get_name.

- [ ] **Step 3: Create dingtalk_adapter.py**

Implement using DingTalk API:
- `get_access_token()`: POST /v1.0/oauth2/accessToken
- `send_group_card()`: POST /v1.0/card/instances — translate CardData to DingTalk card JSON
- `update_group_card()`: PUT /v1.0/card/instances
- `send_private_message()`: POST /v1.0/robot/oToMessages/batchSend
- `download_file()`: POST /v1.0/robot/messageFiles/download

Include retry with exponential backoff (1s/2s/4s, max 3).

- [ ] **Step 4: Create wecom_adapter.py**

Stub implementation raising NotImplementedError for all methods.

- [ ] **Step 5: Run tests**

Run: `cd middleware && python -m pytest tests/test_dingtalk_adapter.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add middleware/app/adapters/
git commit -m "feat(middleware): DingTalk adapter with card + message APIs"
```

---

## Task 7: Event gateway

**Files:**
- Create: `middleware/app/gateway/__init__.py`
- Create: `middleware/app/gateway/dedup.py`
- Create: `middleware/app/gateway/feishu.py`
- Create: `middleware/app/gateway/dingtalk.py`
- Create: `middleware/app/gateway/router.py`
- Test: `middleware/tests/test_gateway.py`

- [ ] **Step 1: Write failing test for Feishu webhook endpoint**

```python
# tests/test_gateway.py
from unittest.mock import MagicMock

def test_feishu_webhook_creates_task(client, db_session):
    """POST /webhook/feishu with valid event → 200 + task_instance created"""
    from app.models.tables import TaskRoute
    route = TaskRoute(handler_name="MockHandler", feishu_table_id="tbl_test",
                      platform="dingtalk", group_id="group_1",
                      field_mapping={}, enabled=True)
    db_session.add(route)
    db_session.commit()

    response = client.post("/webhook/feishu", json={
        "event": {"table_id": "tbl_test", "record_id": "rec_1", "action": "create"},
        "data": {"fields": {"任务标题": "Test"}}
    })
    assert response.status_code == 200
```

Note: Gateway routes delegate to TaskEngine.dispatch(), which was built in Task 5.

- [ ] **Step 2: Create dedup.py**

In-memory dedup with TTL: `set[str]` of processed event keys, expired after 300s. `is_duplicate(key) -> bool`, `mark_processed(key)`.

- [ ] **Step 3: Create feishu.py**

Parse Feishu webhook payload: extract table_id, record_id, action, fields. Verify verification_token from config.

- [ ] **Step 4: Create dingtalk.py**

Parse DingTalk callback: extract card_id, user_id, action value. P0 handles card callback (button click) only.

- [ ] **Step 5: Create router.py with FastAPI routes**

```python
# POST /webhook/feishu - receive Feishu automation webhook
# POST /webhook/dingtalk/callback - receive DingTalk card callback
# GET /webhook/dingtalk/callback - DingTalk URL verification (echo challenge)
```

Gateway routes access TaskEngine via `request.app.state.task_engine`. Include in main.py.

- [ ] **Step 6: Run tests**

Run: `cd middleware && python -m pytest tests/test_gateway.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add middleware/app/gateway/ middleware/app/main.py
git commit -m "feat(middleware): event gateway with Feishu webhook + DingTalk callback"
```

---

## Task 8: Identity mapping service

**Files:**
- Create: `middleware/app/services/__init__.py`
- Create: `middleware/app/services/identity.py`
- Test: `middleware/tests/test_identity.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_identity.py
from app.services.identity import IdentityService

def test_map_feishu_to_dingtalk(db_session):
    svc = IdentityService(db_session)
    # Insert user_mapping
    # svc.get_platform_user_id(feishu_uid="f1", platform="dingtalk") returns "d1"

def test_returns_none_when_no_mapping():
    # svc.get_platform_user_id returns None for unmapped user
    ...
```

- [ ] **Step 2: Create identity.py**

```python
class IdentityService:
    def get_platform_user_id(self, feishu_user_id: str, platform: str) -> str | None
    def get_feishu_user_id(self, platform_user_id: str, platform: str) -> str | None
    def sync_from_feishu(self) -> int  # Pull Feishu contacts, match by phone
    def sync_from_dingtalk(self) -> int  # Pull DingTalk contacts, match by phone
    def auto_match(self) -> int  # Match by phone number across platforms
```

P0 implements `get_platform_user_id` (query user_mapping table) and `auto_match` (join by phone). Actual Feishu/DingTalk API calls are stubbed with TODO comments.

- [ ] **Step 3: Run tests**

Run: `cd middleware && python -m pytest tests/test_identity.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add middleware/app/services/
git commit -m "feat(middleware): identity mapping service with phone auto-match"
```

---

## Task 9: Message queue

**Files:**
- Create: `middleware/app/services/message_queue.py`
- Test: `middleware/tests/test_message_queue.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_message_queue.py
import time
from unittest.mock import MagicMock
from app.services.message_queue import MessageQueue

def test_queue_processes_all_messages():
    q = MessageQueue(rate_per_minute=600)  # high rate for fast test
    sent = []
    def sender(msg):
        sent.append(msg)

    for i in range(5):
        q.enqueue(sender, f"msg_{i}")

    q.drain()  # process all pending
    assert len(sent) == 5
    assert sent == ["msg_0", "msg_1", "msg_2", "msg_3", "msg_4"]

def test_queue_respects_rate_limit():
    q = MessageQueue(rate_per_minute=60)  # 1 per second
    sent = []
    def sender(msg):
        sent.append(msg)

    for i in range(3):
        q.enqueue(sender, f"msg_{i}")

    start = time.time()
    q.drain()
    elapsed = time.time() - start
    # 3 messages at 1/sec should take at least 2 seconds (gaps between sends)
    assert elapsed >= 1.5  # allow small margin
```

- [ ] **Step 2: Create message_queue.py**

Synchronous rate-limited queue for P0: `collections.deque` + `time.sleep` for rate control. `enqueue(callback, *args)` adds to queue. `drain()` processes all pending items at the configured rate. Async version deferred to P1 when integrating real platform APIs.

- [ ] **Step 3: Run tests**

Run: `cd middleware && python -m pytest tests/test_message_queue.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add middleware/app/services/message_queue.py
git commit -m "feat(middleware): rate-limited async message queue"
```

---

## Task 10: Admin API (routes CRUD)

**Files:**
- Create: `middleware/app/admin/__init__.py`
- Create: `middleware/app/admin/auth.py`
- Create: `middleware/app/admin/routes_api.py`
- Test: `middleware/tests/test_admin_api.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_admin_api.py

def test_list_routes_empty(client):
    resp = client.get("/api/routes", headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_route(client, db_session):
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_1",
        "platform": "dingtalk",
        "group_id": "group_1",
        "field_mapping": {"title": "task_title"},
        "enabled": True
    }, headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 201

def test_list_handlers(client):
    resp = client.get("/api/handlers", headers={"Authorization": "Bearer changeme"})
    assert resp.status_code == 200
    # Returns list of registered handler names
```

- [ ] **Step 2: Create auth.py**

Simple Bearer token dependency: reads `settings.admin_token`, validates against `Authorization: Bearer <token>` header.

- [ ] **Step 3: Create routes_api.py**

CRUD endpoints per spec:
- `GET /api/routes` — list all routes
- `POST /api/routes` — create route (validate handler_name exists in registry)
- `PUT /api/routes/{id}` — update route
- `DELETE /api/routes/{id}` — delete route
- `GET /api/handlers` — list registered handler names

Mount in main.py.

- [ ] **Step 4: Run tests**

Run: `cd middleware && python -m pytest tests/test_admin_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add middleware/app/admin/ middleware/app/main.py
git commit -m "feat(middleware): admin API for route CRUD + handler listing"
```

---

## Task 11: Integration test (end-to-end)

**Files:**
- Create: `middleware/tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""End-to-end: Feishu webhook → route lookup → handler → DingTalk adapter"""
from unittest.mock import AsyncMock, patch

def test_feishu_to_dingtalk_e2e(client, db_session):
    # 1. Register a test handler in registry
    # 2. Create a route via admin API
    # 3. POST /webhook/feishu with event
    # 4. Assert task_instance created in DB
    # 5. Assert DingTalk adapter.send_group_card was called
    # 6. Assert task_participant rows created
    pass

def test_dingtalk_callback_updates_task(client, db_session):
    # 1. Create task_instance + participant
    # 2. POST /webhook/dingtalk/callback with card click
    # 3. Assert participant status updated
    # 4. Assert adapter.update_group_card was called
    pass
```

- [ ] **Step 2: Implement and run**

Run: `cd middleware && python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add middleware/tests/test_integration.py
git commit -m "test(middleware): end-to-end integration tests"
```

---

## Task 12: Wire everything in main.py + Dockerfile

**Files:**
- Modify: `middleware/app/main.py`
- Create: `middleware/Dockerfile`

- [ ] **Step 1: Update main.py to wire all components**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)

    # Handler registry
    registry = HandlerRegistry()
    registry.auto_discover("app/handlers")

    # Adapters
    adapters = {
        "dingtalk": DingTalkAdapter(settings.dingtalk_app_key, settings.dingtalk_app_secret, settings.dingtalk_robot_code),
        "wecom": WeComAdapter(),  # stub
    }

    # TaskEngine stored on app.state for gateway routes to access
    app.state.task_engine = TaskEngine(db=SessionLocal(), registry=registry, adapters=adapters)
    app.state.handler_registry = registry

    yield
```

- Import and include gateway router and admin router
- Gateway routes access TaskEngine via `request.app.state.task_engine`
- Admin routes access registry via `request.app.state.handler_registry`

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Run all tests**

Run: `cd middleware && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add middleware/
git commit -m "feat(middleware): wire all components + Dockerfile"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | Project scaffolding | FastAPI app + config + test setup |
| 2 | Database models | 6 tables SQLAlchemy ORM |
| 3 | Core types | TaskData, CardData, etc. |
| 4 | Handler system | BaseHandler ABC + auto-discovery registry |
| 5 | Event gateway | Feishu webhook + DingTalk callback endpoints |
| 6 | DingTalk adapter | Card creation/update, message sending, retry |
| 7 | Task engine | dispatch (route→handler→adapter) + callback |
| 8 | Identity service | User mapping + phone auto-match |
| 9 | Message queue | Rate-limited async queue |
| 10 | Admin API | Route CRUD + handler listing + auth |
| 11 | Integration test | E2E Feishu→DingTalk flow |
| 12 | Wiring + Docker | Full app assembly + container |

**Deferred to P1:** Compensation sync (5-min Feishu polling), APScheduler dependency, file manager, reminder scheduler, WeCom real implementation. These are spec'd but not needed for the P0 skeleton milestone.
