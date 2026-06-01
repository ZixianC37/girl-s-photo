# 产品研发模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现产品研发任务管理模块——支持主任务+子任务创建、自动下发钉钉群卡片、参与者互动确认。

**Architecture:** 新增 2 张表（rd_task, rd_sub_task）+ RDTaskHandler + CRUD API + 前端页面。保存时自动为每个子任务创建 task_route + task_instance 并通过 TaskEngine 下发钉钉卡片。

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy / React 18 / Ant Design 5

**Spec:** `docs/superpowers/specs/2026-05-29-product-dev-module-design.md`

---

## File Structure

```
中台/
├── app/
│   ├── models/tables.py              # 新增 RDTask, RDSubTask
│   ├── handlers/
│   │   └── rd_task_handler.py        # 新增：RDTaskHandler
│   ├── admin/
│   │   └── rd_tasks_api.py           # 新增：CRUD + 自动下发
│   └── main.py                       # 已有（无需修改，handler auto-discover）
├── web/src/
│   ├── api/rdTasks.ts                # 新增：API 函数
│   ├── pages/RDTasks.tsx             # 新增：产品研发页面
│   ├── components/AppLayout.tsx      # 修改：新增菜单项
│   └── App.tsx                       # 修改：新增路由
└── tests/
    └── test_rd_tasks_api.py          # 新增
```

---

## Task 1: 数据库模型（RDTask + RDSubTask）

**Files:**
- Modify: `中台/app/models/tables.py`
- Modify: `中台/app/models/__init__.py`
- Modify: `中台/tests/conftest.py`（确保新表被导入）

- [ ] **Step 1: Add RDTask and RDSubTask models to tables.py**

在 tables.py 末尾追加：

```python
class RDTask(Base):
    __tablename__ = "rd_task"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sub_tasks: Mapped[list["RDSubTask"]] = relationship(back_populates="rd_task", cascade="all, delete-orphan")

class RDSubTask(Base):
    __tablename__ = "rd_sub_task"
    id: Mapped[int] = mapped_column(primary_key=True)
    rd_task_id: Mapped[int] = mapped_column(Integer, ForeignKey("rd_task.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    assignees: Mapped[str] = mapped_column(Text, default="[]")
    group_id: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String(20))
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    deliverables: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    task_instance_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    task_route_id: Mapped[int] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    rd_task: Mapped["RDTask"] = relationship(back_populates="sub_tasks")
```

- [ ] **Step 2: Update models/__init__.py to export new models**

- [ ] **Step 3: Run tests to verify tables create**

Run: `cd 中台 && python3 -m pytest tests/test_types.py -v`
Expected: PASS（新增表不影响现有测试）

- [ ] **Step 4: Commit**

```bash
git add app/models/
git commit -m "feat(middleware): RDTask + RDSubTask database models"
```

---

## Task 2: RDTaskHandler

**Files:**
- Create: `中台/app/handlers/rd_task_handler.py`

- [ ] **Step 1: Create RDTaskHandler**

```python
# app/handlers/rd_task_handler.py
import json
from app.engine.handler_base import BaseHandler
from app.models.types import TaskData, CardData, CardSection, CardAction, FlowDefinition, RoleDefinition, ReminderRule, TaskUpdate


class RDTaskHandler(BaseHandler):

    def parse_event(self, event, field_mapping):
        if isinstance(field_mapping, str):
            field_mapping = json.loads(field_mapping)
        return TaskData(
            title=field_mapping.get("title", "研发子任务"),
            participants=field_mapping.get("assignees", []),
            deadline=None,
            parameters={
                "rd_sub_task_id": field_mapping.get("rd_sub_task_id"),
                "deliverables": field_mapping.get("deliverables", []),
            },
        )

    def get_flow(self):
        return FlowDefinition(
            states=["pending", "confirmed", "submitted", "completed"],
            initial="pending",
        )

    def get_roles(self):
        return RoleDefinition(roles=["creator", "assignee"], default_role="assignee")

    def build_card(self, task, state):
        sections = []
        if task.deadline:
            sections.append(CardSection(text=f"截止时间：{task.deadline.strftime('%Y-%m-%d')}"))

        deliverables = task.flow_state.get("deliverables", []) if isinstance(task.flow_state, dict) else []
        if isinstance(task.flow_state, str):
            try:
                flow = json.loads(task.flow_state)
                deliverables = flow.get("deliverables", [])
            except (json.JSONDecodeError, TypeError):
                pass

        if deliverables:
            items = [f"{d['name']} × {d.get('count', 1)}" for d in deliverables]
            sections.append(CardSection(text=f"交付物：{', '.join(items)}"))

        actions = []
        if state == "pending":
            actions.append(CardAction(label="确认接单", action="confirm", style="primary"))
        elif state == "confirmed":
            actions.append(CardAction(label="上传文件", action="upload"))

        return CardData(
            title=f"子任务：{task.handler_name}",
            sections=sections,
            actions=actions,
        )

    def get_reminder_rules(self):
        return [
            ReminderRule(trigger="time_elapsed", target="private", message_template="您有未完成的研发子任务"),
        ]

    def handle_callback(self, action, user, task):
        status_map = {"confirm": "confirmed", "upload": "submitted"}
        return TaskUpdate(status=status_map.get(action, None))
```

- [ ] **Step 2: Verify handler auto-discovers**

Run: `cd 中台 && python3 -c "from app.engine.registry import HandlerRegistry; r = HandlerRegistry(); r.auto_discover('app/handlers'); print(r.list_handlers())"`
Expected: `['RDTaskHandler']`

- [ ] **Step 3: Commit**

```bash
git add app/handlers/rd_task_handler.py
git commit -m "feat(middleware): RDTaskHandler with card building and callback handling"
```

---

## Task 3: 产品研发 API

**Files:**
- Create: `中台/app/admin/rd_tasks_api.py`
- Modify: `中台/app/main.py`（挂载路由）
- Test: `中台/tests/test_rd_tasks_api.py`

- [ ] **Step 1: Write failing tests**

```python
AUTH = {"Authorization": "Bearer changeme"}

def test_create_rd_task(client, db_session):
    resp = client.post("/api/rd-tasks", json={
        "title": "春季新品研发",
        "description": "2026春季新品",
        "sub_tasks": [
            {"title": "样片拍摄", "assignees": ["f1"], "group_id": "g1", "platform": "dingtalk", "deadline": "2026-12-31T00:00:00Z", "deliverables": [{"name": "样片", "type": "image", "count": 3}], "sort_order": 1}
        ]
    }, headers=AUTH)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "春季新品研发"
    assert len(data["sub_tasks"]) == 1

def test_list_rd_tasks(client, db_session):
    test_create_rd_task(client, db_session)
    resp = client.get("/api/rd-tasks", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

def test_get_rd_task_detail(client, db_session):
    created = test_create_rd_task(client, db_session)
    tid = created.json()["id"]
    resp = client.get(f"/api/rd-tasks/{tid}", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()["sub_tasks"]) == 1

def test_delete_rd_task(client, db_session):
    created = test_create_rd_task(client, db_session)
    tid = created.json()["id"]
    resp = client.delete(f"/api/rd-tasks/{tid}", headers=AUTH)
    assert resp.status_code == 200
```

- [ ] **Step 2: Create rd_tasks_api.py**

CRUD 端点 + 自动下发逻辑。POST 时为每个子任务创建 task_route 并调用 TaskEngine.dispatch()。

核心下发逻辑：
```python
def _dispatch_sub_task(self, sub_task, db, task_engine):
    import json
    # 创建 task_route
    route = TaskRoute(
        handler_name="RDTaskHandler",
        feishu_table_id=f"rd_sub_task:{sub_task.id}",
        platform=sub_task.platform,
        group_id=sub_task.group_id,
        field_mapping=json.dumps({
            "rd_sub_task_id": sub_task.id,
            "title": sub_task.title,
            "assignees": json.loads(sub_task.assignees),
            "deliverables": json.loads(sub_task.deliverables),
        }),
        enabled=True,
    )
    db.add(route)
    db.flush()

    # 构造合成事件并 dispatch
    instance = task_engine.dispatch(
        table_id=f"rd_sub_task:{sub_task.id}",
        record_id=f"rd_sub_task_{sub_task.id}",
        action="create",
        fields=json.loads(sub_task.assignees),
    )

    if instance:
        sub_task.task_instance_id = instance.id
        sub_task.task_route_id = route.id
        sub_task.status = "dispatched"
```

- [ ] **Step 3: Mount router in main.py**

```python
from app.admin.rd_tasks_api import router as rd_tasks_router
app.include_router(rd_tasks_router)
```

- [ ] **Step 4: Run tests**

Run: `cd 中台 && python3 -m pytest tests/test_rd_tasks_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/admin/rd_tasks_api.py app/main.py tests/test_rd_tasks_api.py
git commit -m "feat(middleware): product dev task CRUD API with auto-dispatch"
```

---

## Task 4: 前端 API + 页面

**Files:**
- Create: `中台/web/src/api/rdTasks.ts`
- Create: `中台/web/src/pages/RDTasks.tsx`
- Modify: `中台/web/src/components/AppLayout.tsx`（新增菜单项）
- Modify: `中台/web/src/App.tsx`（新增路由）

- [ ] **Step 1: Create rdTasks.ts API client**

```ts
import client from './client';

export interface RDSubTask {
  id?: number;
  title: string;
  description?: string;
  assignees: string[];
  group_id: string;
  platform: string;
  deadline: string;
  deliverables: { name: string; type: string; count: number }[];
  sort_order: number;
  status?: string;
  task_instance_id?: number;
  progress?: { total_participants: number; confirmed: number; submitted: number };
}

export interface RDTask {
  id: number;
  title: string;
  description: string;
  status: string;
  created_at: string;
  sub_tasks: RDSubTask[];
}

export const listRDTasks = () => client.get<RDTask[]>('/api/rd-tasks').then(r => r.data);
export const getRDTask = (id: number) => client.get<RDTask>(`/api/rd-tasks/${id}`).then(r => r.data);
export const createRDTask = (data: { title: string; description?: string; sub_tasks: RDSubTask[] }) => client.post('/api/rd-tasks', data).then(r => r.data);
export const deleteRDTask = (id: number) => client.delete(`/api/rd-tasks/${id}`).then(r => r.data);
```

- [ ] **Step 2: Create RDTasks.tsx page**

产品研发页面包含：
- 主任务列表（GlassCard 卡片式，显示标题、子任务数、状态、进度）
- 新建弹窗：主任务信息 + 子任务列表编辑器
- 详情视图：子任务列表 + 状态 + 进度

- [ ] **Step 3: Update AppLayout.tsx — 新增菜单项**

在菜单中添加：
```ts
{ key: '/rd-tasks', icon: <ExperimentOutlined />, label: '产品研发' },
```

- [ ] **Step 4: Update App.tsx — 新增路由**

```tsx
const RDTasks = lazy(() => import('./pages/RDTasks'));
// 在 Route 中添加：
<Route path="/rd-tasks" element={<RDTasks />} />
```

- [ ] **Step 5: Build and verify**

Run: `cd 中台/web && npm run build`

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): product dev task management page with sub-task editor"
```

---

## Summary

| Task | Component | Key Deliverable |
|------|-----------|----------------|
| 1 | 数据库模型 | RDTask + RDSubTask 表 |
| 2 | RDTaskHandler | 卡片构建 + 回调处理 |
| 3 | 后端 API | CRUD + 自动下发逻辑 |
| 4 | 前端页面 | 产品研发管理页 + 子任务编辑器 |
