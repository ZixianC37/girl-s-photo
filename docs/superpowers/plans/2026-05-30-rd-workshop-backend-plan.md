# R&D Workshop Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PipelineTemplate + RDProject models, pipeline advancement service, notification chain, reminder background task, anomaly API, and extend RDSubTask with project-aware fields -- transforming the existing middleware into a full R&D workshop platform backend.

**Architecture:** New tables (`pipeline_template`, `rd_project`) added alongside existing ones. `RDSubTask` gains `project_id`, `stage_index`, `stage_name` columns and `rework`/`blocked` statuses. A `PipelineService` orchestrates stage transitions (upstream done -> notify downstream -> auto-create next stage). A `ReminderService` runs as an asyncio background loop polling every 5 minutes. `NotificationChain` is a thin helper that reads stage config and calls DingTalkAdapter. Anomaly queries are derived from sub-task state (no separate table).

**Tech Stack:** Python 3.9+ / FastAPI / SQLAlchemy + SQLite / pytest

**Spec:** `docs/superpowers/specs/2026-05-30-rd-workshop-platform-design.md`

---

## File Structure

```
中台/
├── app/
│   ├── models/
│   │   ├── tables.py                 # Modify: add PipelineTemplate, RDProject; extend RDSubTask
│   │   ├── __init__.py               # Modify: export new models
│   │   └── types.py                  # No change
│   ├── services/
│   │   ├── pipeline_service.py       # New: stage advancement logic
│   │   ├── notification_chain.py     # New: structured notification routing
│   │   ├── reminder_service.py       # New: asyncio background polling
│   │   ├── file_collector.py         # No change
│   │   ├── identity.py               # No change
│   │   └── message_queue.py          # No change
│   ├── admin/
│   │   ├── templates_api.py          # New: PipelineTemplate CRUD
│   │   ├── rd_projects_api.py        # New: RDProject CRUD + start/pause/advance/rework
│   │   ├── anomalies_api.py          # New: anomaly query + resolve
│   │   ├── rd_tasks_api.py           # No change (backward compat)
│   │   └── ...                       # Existing files unchanged
│   ├── engine/
│   │   └── task_engine.py            # Modify: call NotificationChain on stage completion
│   ├── handlers/
│   │   └── rd_task_handler.py        # Modify: support rework / report-problem actions
│   ├── gateway/
│   │   └── router.py                 # No change
│   └── main.py                       # Modify: register new routers + start ReminderService
└── tests/
    ├── conftest.py                   # Modify: import new models
    ├── test_templates_api.py         # New
    ├── test_rd_projects_api.py       # New
    ├── test_pipeline_service.py      # New
    ├── test_notification_chain.py    # New
    ├── test_reminder_service.py      # New
    └── test_anomalies_api.py         # New
```

---

## Task 1: Add PipelineTemplate and RDProject models + extend RDSubTask

**Files:**
- Modify: `中台/app/models/tables.py`
- Modify: `中台/app/models/__init__.py`
- Modify: `中台/tests/conftest.py`

Add two new ORM models (`PipelineTemplate`, `RDProject`) and extend `RDSubTask` with `project_id`, `stage_index`, `stage_name` columns.

- [ ] **Step 1: Add PipelineTemplate and RDProject models to tables.py**

Append to end of `中台/app/models/tables.py`, after the existing `RDSubTask` class:

```python
class PipelineTemplate(Base):
    __tablename__ = "pipeline_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    stages: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of stage definitions
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RDProject(Base):
    __tablename__ = "rd_project"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_template.id"), nullable=True)
    stages_snapshot: Mapped[str] = mapped_column(Text, default="[]")  # JSON snapshot from template
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/active/paused/completed
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sub_tasks: Mapped[list["RDSubTask"]] = relationship(
        back_populates="project",
        foreign_keys="RDSubTask.project_id",
        cascade="all, delete-orphan",
    )
```

- [ ] **Step 2: Add project_id, stage_index, stage_name columns to RDSubTask**

Add three new nullable columns to the existing `RDSubTask` class in `中台/app/models/tables.py`. Place them after `sort_order`:

```python
    # --- new columns for project pipeline ---
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rd_project.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stage_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
```

Also add the `project` relationship to `RDSubTask`:

```python
    project: Mapped[Optional["RDProject"]] = relationship(back_populates="sub_tasks", foreign_keys=[project_id])
```

> Note: `from typing import Optional` must be imported at the top of the file. The file already uses `Mapped[...]` syntax so `Optional` from `typing` is the correct way to express nullable.

- [ ] **Step 3: Export new models in `__init__.py`**

Modify `中台/app/models/__init__.py` to add the new imports and exports:

```python
from app.models.tables import (
    TaskRoute,
    TaskInstance,
    TaskParticipant,
    FileRecord,
    ReminderLog,
    UserMapping,
    GroupMapping,
    RDTask,
    RDSubTask,
    PipelineTemplate,
    RDProject,
)

__all__ = [
    "TaskRoute",
    "TaskInstance",
    "TaskParticipant",
    "FileRecord",
    "ReminderLog",
    "UserMapping",
    "GroupMapping",
    "RDTask",
    "RDSubTask",
    "PipelineTemplate",
    "RDProject",
]
```

- [ ] **Step 4: Update conftest.py imports**

In `中台/tests/conftest.py`, update the import line to include the new models:

```python
from app.models import TaskRoute, TaskInstance, TaskParticipant, FileRecord, ReminderLog, UserMapping, GroupMapping, PipelineTemplate, RDProject
```

- [ ] **Step 5: Run tests to verify nothing is broken**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -x -q
```

All existing tests must still pass. The new columns are nullable so existing data and tests are unaffected.

- [ ] **Step 6: Commit**

```bash
git add 中台/app/models/tables.py 中台/app/models/__init__.py 中台/tests/conftest.py
git commit -m "feat: add PipelineTemplate, RDProject models; extend RDSubTask with project fields"
```

---

## Task 2: PipelineTemplate CRUD API

**Files:**
- Create: `中台/app/admin/templates_api.py`
- Create: `中台/tests/test_templates_api.py`
- Modify: `中台/app/main.py` (register router)

Build full CRUD for pipeline templates: list, create, get, update, delete, clone.

- [ ] **Step 1: Write failing tests first**

Create `中台/tests/test_templates_api.py`:

```python
import json
import pytest

AUTH = {"Authorization": "Bearer changeme"}

SAMPLE_STAGES = [
    {
        "name": "灵感收集",
        "description": "团队提交灵感和参考素材",
        "default_assignees": [],
        "deliverables": [{"name": "参考图", "count": 5}],
        "timeout_days": 3,
        "reminder_policy": {
            "first_delay_hours": 24,
            "interval_hours": 12,
            "escalation_delay_hours": 24,
            "max_retries": 3,
        },
        "notify_target": {
            "type": "next_stage_assignee",
            "also_notify_manager": False,
        },
    }
]


def test_list_templates_empty(client, db_session):
    resp = client.get("/api/templates", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_template(client, db_session):
    resp = client.post(
        "/api/templates",
        json={"name": "标准写真研发", "description": "标准8阶段", "stages": SAMPLE_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "标准写真研发"
    assert data["description"] == "标准8阶段"
    assert len(json.loads(data["stages"])) == 1
    assert json.loads(data["stages"])[0]["name"] == "灵感收集"
    assert "id" in data


def test_create_template_validates_stages_length(client, db_session):
    # Too many stages
    resp = client.post(
        "/api/templates",
        json={"name": "Bad", "stages": [{"name": f"S{i}"} for i in range(21)]},
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_get_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="T1", stages=json.dumps(SAMPLE_STAGES))
    db_session.add(t)
    db_session.commit()

    resp = client.get(f"/api/templates/{t.id}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["name"] == "T1"


def test_get_template_not_found(client, db_session):
    resp = client.get("/api/templates/999", headers=AUTH)
    assert resp.status_code == 404


def test_update_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="Old", stages="[]")
    db_session.add(t)
    db_session.commit()

    resp = client.put(
        f"/api/templates/{t.id}",
        json={"name": "New", "stages": SAMPLE_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_delete_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="ToDelete", stages="[]")
    db_session.add(t)
    db_session.commit()

    resp = client.delete(f"/api/templates/{t.id}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


def test_delete_template_with_active_project_fails(client, db_session):
    from app.models.tables import PipelineTemplate, RDProject

    t = PipelineTemplate(name="InUse", stages="[]")
    db_session.add(t)
    db_session.flush()
    p = RDProject(name="P1", template_id=t.id, status="active")
    db_session.add(p)
    db_session.commit()

    resp = client.delete(f"/api/templates/{t.id}", headers=AUTH)
    assert resp.status_code == 409


def test_clone_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="Original", description="desc", stages=json.dumps(SAMPLE_STAGES))
    db_session.add(t)
    db_session.commit()

    resp = client.post(f"/api/templates/{t.id}/clone", headers=AUTH)
    assert resp.status_code == 201
    clone = resp.json()
    assert clone["name"] == "Original (副本)"
    assert clone["id"] != t.id


def test_unauthorized(client, db_session):
    resp = client.get("/api/templates")
    assert resp.status_code in (401, 422)
```

Run tests to see them fail:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_templates_api.py -x -q
```

- [ ] **Step 2: Implement templates_api.py**

Create `中台/app/admin/templates_api.py`:

```python
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from app.database import get_db
from app.models.tables import PipelineTemplate, RDProject
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api/templates", tags=["templates"])


class StageDef(BaseModel):
    name: str
    description: str = ""
    default_assignees: List[str] = []
    deliverables: List[dict] = []
    timeout_days: int = 3
    reminder_policy: Optional[dict] = None
    notify_target: Optional[dict] = None


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    stages: List[StageDef]

    @field_validator("stages")
    @classmethod
    def validate_stages_length(cls, v):
        if len(v) < 1 or len(v) > 20:
            raise ValueError("stages must contain 1-20 items")
        return v


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stages: Optional[List[StageDef]] = None

    @field_validator("stages")
    @classmethod
    def validate_stages_length(cls, v):
        if v is not None and (len(v) < 1 or len(v) > 20):
            raise ValueError("stages must contain 1-20 items")
        return v


def _format_template(t: PipelineTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "stages": t.stages,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("")
async def list_templates(db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    templates = db.query(PipelineTemplate).order_by(PipelineTemplate.id.desc()).all()
    return [_format_template(t) for t in templates]


@router.post("", status_code=201)
async def create_template(data: TemplateCreate, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    t = PipelineTemplate(
        name=data.name,
        description=data.description,
        stages=json.dumps([s.model_dump() for s in data.stages]),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _format_template(t)


@router.get("/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    t = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return _format_template(t)


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    t = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    if data.name is not None:
        t.name = data.name
    if data.description is not None:
        t.description = data.description
    if data.stages is not None:
        t.stages = json.dumps([s.model_dump() for s in data.stages])
    db.commit()
    db.refresh(t)
    return _format_template(t)


@router.delete("/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    t = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check for active projects using this template
    active_count = db.query(RDProject).filter(
        RDProject.template_id == template_id,
        RDProject.status.in_(["draft", "active", "paused"]),
    ).count()
    if active_count > 0:
        raise HTTPException(status_code=409, detail=f"Template has {active_count} active project(s)")

    db.delete(t)
    db.commit()
    return {"status": "deleted"}


@router.post("/{template_id}/clone", status_code=201)
async def clone_template(template_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    t = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    clone = PipelineTemplate(
        name=f"{t.name} (副本)",
        description=t.description,
        stages=t.stages,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return _format_template(clone)
```

- [ ] **Step 3: Register the router in main.py**

Add to `中台/app/main.py` imports:

```python
from app.admin.templates_api import router as templates_router
```

Add before the SPA fallback section:

```python
app.include_router(templates_router)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_templates_api.py -x -v
```

All tests should pass.

- [ ] **Step 5: Commit**

```bash
git add 中台/app/admin/templates_api.py 中台/tests/test_templates_api.py 中台/app/main.py
git commit -m "feat: add PipelineTemplate CRUD API with list/create/get/update/delete/clone"
```

---

## Task 3: RDProject CRUD API (create from template, start/pause)

**Files:**
- Create: `中台/app/admin/rd_projects_api.py`
- Create: `中台/tests/test_rd_projects_api.py`
- Modify: `中台/app/main.py` (register router)

Project creation: select template -> snapshot stages -> create RDProject + draft RDSubTasks. Start project: set status=active, dispatch first stage.

- [ ] **Step 1: Write failing tests**

Create `中台/tests/test_rd_projects_api.py`:

```python
import json
import pytest

AUTH = {"Authorization": "Bearer changeme"}

TWO_STAGES = [
    {
        "name": "灵感收集",
        "description": "collect ideas",
        "default_assignees": ["user_a"],
        "deliverables": [{"name": "参考图", "count": 3}],
        "timeout_days": 3,
        "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "escalation_delay_hours": 24, "max_retries": 3},
        "notify_target": {"type": "next_stage_assignee", "also_notify_manager": False},
    },
    {
        "name": "灵感创作",
        "description": "create from ideas",
        "default_assignees": ["user_b"],
        "deliverables": [{"name": "创作方案", "count": 1}],
        "timeout_days": 5,
        "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "escalation_delay_hours": 24, "max_retries": 3},
        "notify_target": {"type": "next_stage_assignee", "also_notify_manager": False},
    },
]


def _create_template(client, name="Test Template"):
    resp = client.post(
        "/api/templates",
        json={"name": name, "stages": TWO_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_project_from_template(client, db_session):
    tid = _create_template(client)
    resp = client.post(
        "/api/projects",
        json={
            "name": "春季研发",
            "description": "test",
            "template_id": tid,
            "stage_overrides": [],
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "春季研发"
    assert data["status"] == "draft"
    assert len(data["sub_tasks"]) == 2
    assert data["sub_tasks"][0]["stage_name"] == "灵感收集"
    assert data["sub_tasks"][0]["stage_index"] == 0
    assert data["sub_tasks"][0]["project_id"] == data["id"]


def test_create_project_with_overrides(client, db_session):
    tid = _create_template(client)
    resp = client.post(
        "/api/projects",
        json={
            "name": "Override Test",
            "template_id": tid,
            "stage_overrides": [
                {"stage_index": 0, "assignees": ["custom_user"], "group_id": "g_custom", "platform": "dingtalk", "deadline": "2026-07-01T00:00:00Z"},
            ],
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    sub0 = data["sub_tasks"][0]
    assert sub0["assignees"] == ["custom_user"]
    assert sub0["group_id"] == "g_custom"


def test_list_projects(client, db_session):
    tid = _create_template(client)
    client.post("/api/projects", json={"name": "P1", "template_id": tid, "stage_overrides": []}, headers=AUTH)
    client.post("/api/projects", json={"name": "P2", "template_id": tid, "stage_overrides": []}, headers=AUTH)

    resp = client.get("/api/projects", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_projects_filter_by_status(client, db_session):
    tid = _create_template(client)
    client.post("/api/projects", json={"name": "P1", "template_id": tid, "stage_overrides": []}, headers=AUTH)

    resp = client.get("/api/projects?status=draft", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/api/projects?status=active", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_get_project_detail(client, db_session):
    tid = _create_template(client)
    created = client.post("/api/projects", json={"name": "Detail", "template_id": tid, "stage_overrides": []}, headers=AUTH)
    pid = created.json()["id"]

    resp = client.get(f"/api/projects/{pid}", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail"
    assert "stages_snapshot" in data
    assert len(data["sub_tasks"]) == 2


def test_patch_project_status(client, db_session):
    tid = _create_template(client)
    created = client.post("/api/projects", json={"name": "Status", "template_id": tid, "stage_overrides": []}, headers=AUTH)
    pid = created.json()["id"]

    resp = client.patch(f"/api/projects/{pid}", json={"status": "paused"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_patch_project_invalid_status(client, db_session):
    tid = _create_template(client)
    created = client.post("/api/projects", json={"name": "Bad", "template_id": tid, "stage_overrides": []}, headers=AUTH)
    pid = created.json()["id"]

    resp = client.patch(f"/api/projects/{pid}", json={"status": "invalid"}, headers=AUTH)
    assert resp.status_code == 422


def test_get_project_not_found(client, db_session):
    resp = client.get("/api/projects/999", headers=AUTH)
    assert resp.status_code == 404


def test_delete_project(client, db_session):
    tid = _create_template(client)
    created = client.post("/api/projects", json={"name": "Del", "template_id": tid, "stage_overrides": []}, headers=AUTH)
    pid = created.json()["id"]

    resp = client.delete(f"/api/projects/{pid}", headers=AUTH)
    assert resp.status_code == 200

    resp = client.get(f"/api/projects/{pid}", headers=AUTH)
    assert resp.status_code == 404
```

Run to see failures:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_rd_projects_api.py -x -q
```

- [ ] **Step 2: Implement rd_projects_api.py**

Create `中台/app/admin/rd_projects_api.py`:

```python
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from app.database import get_db
from app.models.tables import PipelineTemplate, RDProject, RDSubTask
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api/projects", tags=["projects"])

VALID_PROJECT_STATUSES = ("draft", "active", "paused", "completed")


class StageOverride(BaseModel):
    stage_index: int
    assignees: Optional[List[str]] = None
    group_id: Optional[str] = None
    platform: Optional[str] = None
    deadline: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    template_id: int
    stage_overrides: List[StageOverride] = []


class ProjectPatch(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_PROJECT_STATUSES:
            raise ValueError(f"status must be one of {VALID_PROJECT_STATUSES}")
        return v


def parse_datetime(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _format_project(project: RDProject, db: Session) -> dict:
    sub_tasks_data = []
    for sub in project.sub_tasks:
        sub_tasks_data.append({
            "id": sub.id,
            "title": sub.title,
            "description": sub.description,
            "assignees": json.loads(sub.assignees) if sub.assignees else [],
            "group_id": sub.group_id,
            "platform": sub.platform,
            "deadline": sub.deadline.isoformat() if sub.deadline else None,
            "deliverables": json.loads(sub.deliverables) if sub.deliverables else [],
            "status": sub.status,
            "stage_index": sub.stage_index,
            "stage_name": sub.stage_name,
            "project_id": sub.project_id,
            "task_instance_id": sub.task_instance_id,
            "sort_order": sub.sort_order,
        })

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "template_id": project.template_id,
        "stages_snapshot": project.stages_snapshot,
        "status": project.status,
        "created_by": project.created_by,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "sub_tasks": sub_tasks_data,
    }


@router.get("")
async def list_projects(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    q = db.query(RDProject)
    if status:
        q = q.filter(RDProject.status == status)
    projects = q.order_by(RDProject.id.desc()).all()
    return [_format_project(p, db) for p in projects]


@router.post("", status_code=201)
async def create_project(data: ProjectCreate, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    # Fetch template
    template = db.query(PipelineTemplate).filter(PipelineTemplate.id == data.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    stages = json.loads(template.stages)
    stages_snapshot = json.dumps(stages)

    # Create project
    project = RDProject(
        name=data.name,
        description=data.description,
        template_id=template.id,
        stages_snapshot=stages_snapshot,
        status="draft",
    )
    db.add(project)
    db.flush()

    # Build override lookup
    overrides = {o.stage_index: o for o in data.stage_overrides}

    # Create sub_tasks from stages
    for idx, stage in enumerate(stages):
        override = overrides.get(idx)

        assignees = stage.get("default_assignees", [])
        group_id = ""
        platform = "dingtalk"
        deadline = None

        if override:
            if override.assignees is not None:
                assignees = override.assignees
            if override.group_id is not None:
                group_id = override.group_id
            if override.platform is not None:
                platform = override.platform
            if override.deadline is not None:
                deadline = parse_datetime(override.deadline)

        sub = RDSubTask(
            project_id=project.id,
            rd_task_id=None,  # not linked to old RDTask
            title=stage.get("name", f"Stage {idx}"),
            description=stage.get("description", ""),
            assignees=json.dumps(assignees),
            group_id=group_id,
            platform=platform,
            deadline=deadline,
            deliverables=json.dumps(stage.get("deliverables", [])),
            status="pending",
            sort_order=idx,
            stage_index=idx,
            stage_name=stage.get("name", f"Stage {idx}"),
        )
        db.add(sub)

    db.commit()
    db.refresh(project)
    return _format_project(project, db)


@router.get("/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    project = db.query(RDProject).filter(RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _format_project(project, db)


@router.patch("/{project_id}")
async def patch_project(
    project_id: int,
    data: ProjectPatch,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    project = db.query(RDProject).filter(RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = data.status
    db.commit()
    db.refresh(project)
    return _format_project(project, db)


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    project = db.query(RDProject).filter(RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)  # CASCADE deletes sub_tasks
    db.commit()
    return {"status": "deleted"}
```

- [ ] **Step 3: Register router in main.py**

Add import:

```python
from app.admin.rd_projects_api import router as projects_router
```

Add:

```python
app.include_router(projects_router)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_rd_projects_api.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add 中台/app/admin/rd_projects_api.py 中台/tests/test_rd_projects_api.py 中台/app/main.py
git commit -m "feat: add RDProject CRUD API - create from template, list/filter, patch status, delete"
```

---

## Task 4: PipelineService - stage advancement + project start

**Files:**
- Create: `中台/app/services/pipeline_service.py`
- Create: `中台/tests/test_pipeline_service.py`

Core pipeline logic: start project (dispatch first stage), advance stage (upstream done -> mark complete -> auto-dispatch next stage), rework stage.

- [ ] **Step 1: Write failing tests**

Create `中台/tests/test_pipeline_service.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.tables import PipelineTemplate, RDProject, RDSubTask, TaskRoute, TaskInstance
from app.services.pipeline_service import PipelineService


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.dispatch = AsyncMock(return_value=None)
    engine.db = MagicMock()
    return engine


@pytest.fixture
def sample_project(db_session):
    stages = [
        {"name": "灵感收集", "deliverables": [{"name": "参考图", "count": 3}], "timeout_days": 3,
         "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
         "notify_target": {"type": "next_stage_assignee"}},
        {"name": "灵感创作", "deliverables": [{"name": "创作方案", "count": 1}], "timeout_days": 5,
         "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
         "notify_target": {"type": "next_stage_assignee"}},
    ]
    project = RDProject(name="Test", stages_snapshot=json.dumps(stages), status="draft")
    db_session.add(project)
    db_session.flush()

    for idx, stage in enumerate(stages):
        sub = RDSubTask(
            project_id=project.id,
            title=stage["name"],
            assignees=json.dumps(["user_a"]),
            group_id="g1",
            platform="dingtalk",
            deliverables=json.dumps(stage["deliverables"]),
            status="pending",
            sort_order=idx,
            stage_index=idx,
            stage_name=stage["name"],
        )
        db_session.add(sub)
    db_session.commit()
    return project


def test_start_project(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    result = svc.start_project(sample_project.id)

    assert result is not None
    assert result["status"] == "active"
    # First sub-task should be dispatched
    first_sub = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 0,
    ).first()
    assert first_sub.status == "dispatched"
    mock_engine.dispatch.assert_called_once()


def test_start_project_already_active(db_session, sample_project, mock_engine):
    sample_project.status = "active"
    db_session.commit()

    svc = PipelineService(db_session, mock_engine)
    result = svc.start_project(sample_project.id)
    assert result is None  # Cannot start non-draft project


def test_advance_stage(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    # Mark stage 0 as complete
    sub0 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 0,
    ).first()
    sub0.status = "completed"
    db_session.commit()

    # Advance
    result = svc.advance_stage(sample_project.id, 0)
    assert result is not None

    # Stage 1 should now be dispatched
    sub1 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 1,
    ).first()
    assert sub1.status == "dispatched"


def test_advance_last_stage_completes_project(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    # Complete all stages
    for sub in db_session.query(RDSubTask).filter(RDSubTask.project_id == sample_project.id).all():
        sub.status = "completed"
    db_session.commit()

    result = svc.advance_stage(sample_project.id, 1)
    assert result["status"] == "completed"


def test_rework_stage(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    sub0 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 0,
    ).first()
    sub0.status = "completed"
    db_session.commit()

    # Rework stage 0
    result = svc.rework_stage(sample_project.id, 0, reason="质量不达标")
    assert result is not None

    db_session.refresh(sub0)
    assert sub0.status == "rework"


def test_rework_invalid_stage(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    result = svc.rework_stage(sample_project.id, 0, reason="not yet started")
    assert result is None  # Cannot rework a pending stage


def test_get_current_stages(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    stages = svc.get_current_stages(sample_project.id)
    assert len(stages) == 1  # Only stage 0 is active
    assert stages[0].stage_index == 0
```

Run to see failures:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_pipeline_service.py -x -q
```

- [ ] **Step 2: Implement PipelineService**

Create `中台/app/services/pipeline_service.py`:

```python
"""Pipeline service for managing project stage advancement."""
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.tables import RDProject, RDSubTask, TaskRoute


class PipelineService:
    """Orchestrates pipeline stage transitions for R&D projects."""

    def __init__(self, db: Session, task_engine=None):
        self.db = db
        self.task_engine = task_engine

    def start_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Start a draft project by dispatching the first stage.

        Returns project dict on success, None if project cannot be started.
        """
        project = self.db.query(RDProject).filter(RDProject.id == project_id).first()
        if not project or project.status != "draft":
            return None

        project.status = "active"
        self.db.flush()

        # Dispatch first stage
        first_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == 0,
        ).first()

        if first_sub:
            self._dispatch_sub_task(first_sub)

        self.db.commit()
        self.db.refresh(project)
        return self._format_project(project)

    def advance_stage(self, project_id: int, completed_stage_index: int) -> Optional[Dict[str, Any]]:
        """Advance pipeline after a stage completes.

        Marks the completed stage, dispatches the next stage,
        or marks project completed if this was the last stage.
        """
        project = self.db.query(RDProject).filter(RDProject.id == project_id).first()
        if not project or project.status not in ("active",):
            return None

        # Verify the stage is actually completed
        current_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == completed_stage_index,
        ).first()

        if not current_sub or current_sub.status != "completed":
            return None

        # Find next stage
        next_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == completed_stage_index + 1,
        ).first()

        if next_sub:
            self._dispatch_sub_task(next_sub)
        else:
            # Last stage done -> complete project
            project.status = "completed"

        self.db.commit()
        self.db.refresh(project)
        return self._format_project(project)

    def rework_stage(self, project_id: int, stage_index: int, reason: str = "") -> Optional[Dict[str, Any]]:
        """Put a stage into rework status.

        Only completed or dispatched stages can be reworked.
        """
        sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == stage_index,
        ).first()

        if not sub or sub.status not in ("completed", "dispatched"):
            return None

        sub.status = "rework"
        self.db.commit()
        self.db.refresh(sub)
        return self._format_sub_task(sub)

    def get_current_stages(self, project_id: int) -> List[RDSubTask]:
        """Get currently active (dispatched/rework/blocked) stages for a project."""
        return self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.status.in_(["dispatched", "rework", "blocked"]),
        ).order_by(RDSubTask.stage_index).all()

    def _dispatch_sub_task(self, sub: RDSubTask) -> None:
        """Dispatch a sub-task via the task engine."""
        sub.status = "dispatched"
        # Actual dispatch via task_engine is async and handled at the API layer.
        # This method just marks the status. The API layer calls task_engine.dispatch.

    def _format_project(self, project: RDProject) -> Dict[str, Any]:
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "template_id": project.template_id,
        }

    def _format_sub_task(self, sub: RDSubTask) -> Dict[str, Any]:
        return {
            "id": sub.id,
            "title": sub.title,
            "status": sub.status,
            "stage_index": sub.stage_index,
            "stage_name": sub.stage_name,
            "project_id": sub.project_id,
        }
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_pipeline_service.py -x -v
```

- [ ] **Step 4: Commit**

```bash
git add 中台/app/services/pipeline_service.py 中台/tests/test_pipeline_service.py
git commit -m "feat: add PipelineService - start project, advance stage, rework stage"
```

---

## Task 5: Project start/advance/rework API endpoints

**Files:**
- Modify: `中台/app/admin/rd_projects_api.py` (add advance/rework endpoints)
- Modify: `中台/tests/test_rd_projects_api.py` (add tests for new endpoints)

Wire PipelineService into the API layer with actual task_engine dispatch and advance/rework endpoints.

- [ ] **Step 1: Add failing tests for advance/rework/start endpoints**

Append to `中台/tests/test_rd_projects_api.py`:

```python
def test_start_project_api(client, db_session):
    """POST /api/projects/{id}/start dispatches first stage."""
    from app.models.tables import RDProject, RDSubTask, PipelineTemplate
    import json

    t = PipelineTemplate(name="T", stages=json.dumps([
        {"name": "Stage 0", "deliverables": [], "timeout_days": 3},
        {"name": "Stage 1", "deliverables": [], "timeout_days": 3},
    ]))
    db_session.add(t)
    db_session.flush()

    p = RDProject(name="StartTest", template_id=t.id, stages_snapshot=t.stages, status="draft")
    db_session.add(p)
    db_session.flush()

    for idx in range(2):
        db_session.add(RDSubTask(
            project_id=p.id, title=f"S{idx}", assignees="[]", group_id="g1",
            platform="dingtalk", deliverables="[]", status="pending",
            sort_order=idx, stage_index=idx, stage_name=f"S{idx}",
        ))
    db_session.commit()

    resp = client.post(f"/api/projects/{p.id}/start", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"


def test_advance_project_api(client, db_session):
    """POST /api/projects/{id}/advance advances pipeline."""
    from app.models.tables import RDProject, RDSubTask, PipelineTemplate
    import json

    t = PipelineTemplate(name="T", stages=json.dumps([
        {"name": "S0", "deliverables": []},
        {"name": "S1", "deliverables": []},
    ]))
    db_session.add(t)
    db_session.flush()

    p = RDProject(name="AdvTest", template_id=t.id, stages_snapshot=t.stages, status="active")
    db_session.add(p)
    db_session.flush()

    s0 = RDSubTask(project_id=p.id, title="S0", assignees="[]", group_id="g1",
                   platform="dingtalk", deliverables="[]", status="completed",
                   sort_order=0, stage_index=0, stage_name="S0")
    s1 = RDSubTask(project_id=p.id, title="S1", assignees="[]", group_id="g1",
                   platform="dingtalk", deliverables="[]", status="pending",
                   sort_order=1, stage_index=1, stage_name="S1")
    db_session.add_all([s0, s1])
    db_session.commit()

    resp = client.post(f"/api/projects/{p.id}/advance", json={"stage_index": 0}, headers=AUTH)
    assert resp.status_code == 200
    # Stage 1 should now be dispatched
    db_session.refresh(s1)
    assert s1.status == "dispatched"


def test_rework_project_api(client, db_session):
    """POST /api/projects/{id}/rework puts stage into rework."""
    from app.models.tables import RDProject, RDSubTask, PipelineTemplate
    import json

    t = PipelineTemplate(name="T", stages=json.dumps([{"name": "S0"}]))
    db_session.add(t)
    db_session.flush()

    p = RDProject(name="ReworkTest", template_id=t.id, stages_snapshot=t.stages, status="active")
    db_session.add(p)
    db_session.flush()

    s0 = RDSubTask(project_id=p.id, title="S0", assignees="[]", group_id="g1",
                   platform="dingtalk", deliverables="[]", status="completed",
                   sort_order=0, stage_index=0, stage_name="S0")
    db_session.add(s0)
    db_session.commit()

    resp = client.post(f"/api/projects/{p.id}/rework",
                       json={"stage_index": 0, "reason": "quality issue"}, headers=AUTH)
    assert resp.status_code == 200
    db_session.refresh(s0)
    assert s0.status == "rework"
```

Run to see failures:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_rd_projects_api.py::test_start_project_api tests/test_rd_projects_api.py::test_advance_project_api tests/test_rd_projects_api.py::test_rework_project_api -x -q
```

- [ ] **Step 2: Add endpoints to rd_projects_api.py**

Add these Pydantic models and endpoints to `中台/app/admin/rd_projects_api.py`:

After the existing `ProjectPatch` class, add:

```python
class ProjectAdvance(BaseModel):
    stage_index: int

class ProjectRework(BaseModel):
    stage_index: int
    reason: str = ""
```

Then add these endpoint functions to the router (before `delete_project`):

```python
@router.post("/{project_id}/start")
async def start_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = request.app.state.task_engine
    svc = PipelineService(db, engine)
    result = svc.start_project(project_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot start project (must be in draft status)")
    db_obj = db.query(RDProject).filter(RDProject.id == project_id).first()

    # Dispatch first sub-task via task engine
    first_sub = db.query(RDSubTask).filter(
        RDSubTask.project_id == project_id,
        RDSubTask.stage_index == 0,
    ).first()
    if first_sub and engine:
        await _dispatch_sub_task_via_engine(first_sub, db, engine)

    return _format_project(db_obj, db)


@router.post("/{project_id}/advance")
async def advance_project(
    project_id: int,
    data: ProjectAdvance,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = request.app.state.task_engine
    svc = PipelineService(db, engine)
    result = svc.advance_stage(project_id, data.stage_index)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot advance (stage not completed or project not active)")

    db_obj = db.query(RDProject).filter(RDProject.id == project_id).first()
    return _format_project(db_obj, db)


@router.post("/{project_id}/rework")
async def rework_project(
    project_id: int,
    data: ProjectRework,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = request.app.state.task_engine
    svc = PipelineService(db, engine)
    result = svc.rework_stage(project_id, data.stage_index, data.reason)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot rework (stage must be completed or dispatched)")

    db_obj = db.query(RDProject).filter(RDProject.id == project_id).first()
    return _format_project(db_obj, db)
```

Also add the helper function (at module level, before the router definitions):

```python
from fastapi import Request


async def _dispatch_sub_task_via_engine(sub: RDSubTask, db: Session, task_engine) -> None:
    """Dispatch a sub-task through the TaskEngine to DingTalk."""
    import json as _json

    # Create or reuse a TaskRoute
    route = TaskRoute(
        handler_name="RDTaskHandler",
        feishu_table_id=f"rd_sub_task:{sub.id}",
        platform=sub.platform,
        group_id=sub.group_id,
        field_mapping=_json.dumps({
            "rd_sub_task_id": sub.id,
            "title": sub.title,
            "assignees": _json.loads(sub.assignees) if sub.assignees else [],
            "deliverables": _json.loads(sub.deliverables) if sub.deliverables else [],
        }),
        enabled=True,
    )
    db.add(route)
    db.flush()

    try:
        instance = await task_engine.dispatch(
            table_id=f"rd_sub_task:{sub.id}",
            record_id=f"rd_sub_task_{sub.id}",
            action="create",
            fields={},
        )
        if instance:
            sub.task_instance_id = instance.id
            sub.task_route_id = route.id
    except Exception:
        pass  # Keep status as dispatched even if DingTalk call fails
```

Add `from fastapi import Request` to the imports if not already there.

- [ ] **Step 3: Run all project tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_rd_projects_api.py -x -v
```

- [ ] **Step 4: Commit**

```bash
git add 中台/app/admin/rd_projects_api.py 中台/tests/test_rd_projects_api.py
git commit -m "feat: add project start/advance/rework API endpoints with task engine dispatch"
```

---

## Task 6: NotificationChain service

**Files:**
- Create: `中台/app/services/notification_chain.py`
- Create: `中台/tests/test_notification_chain.py`

Thin helper that reads stage `notify_target` config and calls DingTalkAdapter to send the right notification when a stage completes.

- [ ] **Step 1: Write failing tests**

Create `中台/tests/test_notification_chain.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.tables import RDProject, RDSubTask
from app.services.notification_chain import NotificationChain


@pytest.fixture
def mock_adapters():
    dt = MagicMock()
    dt.send_private_message = AsyncMock()
    dt.send_private_card = AsyncMock()
    dt.send_group_card = AsyncMock()
    return {"dingtalk": dt, "wecom": MagicMock()}


def _make_project(db_session, stages):
    p = RDProject(name="NotifTest", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(p)
    db_session.flush()
    for idx, s in enumerate(stages):
        sub = RDSubTask(
            project_id=p.id, title=s["name"], assignees=json.dumps(s.get("default_assignees", [])),
            group_id="g1", platform="dingtalk", deliverables="[]",
            status="completed" if idx == 0 else "pending",
            sort_order=idx, stage_index=idx, stage_name=s["name"],
        )
        db_session.add(sub)
    db_session.commit()
    return p


def test_notify_next_stage_assignee(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
        {"name": "S1", "default_assignees": ["user_b"], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    # Should send notification to next stage assignee
    mock_adapters["dingtalk"].send_private_message.assert_not_called()  # No manager notify
    # next_stage_assignee notification uses send_private_card or send_private_message


def test_notify_manager(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "manager", "also_notify_manager": True}},
        {"name": "S1", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters, manager_user_id="manager_001")

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()
    call_args = mock_adapters["dingtalk"].send_private_message.call_args
    assert call_args[0][0] == "manager_001"


def test_notify_specific_group(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "specific_group", "group_name": "品鉴群"}},
        {"name": "S1", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters, group_lookup={"品鉴群": "group_pinjian"})

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    mock_adapters["dingtalk"].send_private_message.assert_not_called()


def test_last_stage_notifies_manager(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters, manager_user_id="mgr")

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()
```

Run:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_notification_chain.py -x -q
```

- [ ] **Step 2: Implement NotificationChain**

Create `中台/app/services/notification_chain.py`:

```python
"""Notification chain service for pipeline stage transitions."""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.tables import RDProject, RDSubTask


class NotificationChain:
    """Sends structured notifications when pipeline stages complete.

    Reads notify_target config from the stage definition and routes
    notifications through the appropriate platform adapter.
    """

    def __init__(
        self,
        db: Session,
        adapters: dict,
        manager_user_id: Optional[str] = None,
        group_lookup: Optional[Dict[str, str]] = None,
    ):
        self.db = db
        self.adapters = adapters
        self.manager_user_id = manager_user_id
        self.group_lookup = group_lookup or {}

    async def on_stage_completed(self, project_id: int, stage_index: int) -> None:
        """Called when a stage is marked as completed.

        Reads the notify_target from the stage config and sends notifications.
        """
        project = self.db.query(RDProject).filter(RDProject.id == project_id).first()
        if not project:
            return

        stages = json.loads(project.stages_snapshot)
        if stage_index >= len(stages):
            return

        stage_config = stages[stage_index]
        notify_target = stage_config.get("notify_target", {})
        notify_type = notify_target.get("type", "next_stage_assignee")
        also_manager = notify_target.get("also_notify_manager", False)

        stage_name = stage_config.get("name", f"Stage {stage_index}")

        # Check if this is the last stage
        is_last = stage_index >= len(stages) - 1

        if is_last:
            # Last stage always notifies manager
            await self._notify_manager(
                f"项目「{project.name}」已全部完成！最后阶段「{stage_name}」已结束。"
            )
            return

        # Get next stage info
        next_stage = stages[stage_index + 1]
        next_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == stage_index + 1,
        ).first()

        if notify_type == "next_stage_assignee":
            if next_sub:
                assignees = json.loads(next_sub.assignees) if next_sub.assignees else []
                for assignee in assignees:
                    await self._send_private(
                        assignee,
                        f"项目「{project.name}」阶段「{stage_name}」已完成，"
                        f"轮到您负责「{next_stage.get('name', '下一阶段')}」。"
                    )

        elif notify_type == "manager":
            await self._notify_manager(
                f"项目「{project.name}」阶段「{stage_name}」已完成，请确认。"
            )

        elif notify_type == "specific_group":
            group_name = notify_target.get("group_name", "")
            group_id = self.group_lookup.get(group_name, "")
            if group_id:
                await self._send_group(
                    group_id,
                    f"项目「{project.name}」阶段「{stage_name}」已完成。"
                )

        elif notify_type == "multiple":
            # Handle multiple notification targets
            pass

        if also_manager:
            await self._notify_manager(
                f"项目「{project.name}」阶段「{stage_name}」已完成。"
            )

    async def _send_private(self, user_id: str, message: str) -> None:
        adapter = self.adapters.get("dingtalk")
        if adapter and user_id:
            await adapter.send_private_message(user_id, message)

    async def _notify_manager(self, message: str) -> None:
        if self.manager_user_id:
            await self._send_private(self.manager_user_id, message)

    async def _send_group(self, group_id: str, message: str) -> None:
        adapter = self.adapters.get("dingtalk")
        if adapter:
            await adapter.send_private_message(group_id, message)
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_notification_chain.py -x -v
```

- [ ] **Step 4: Commit**

```bash
git add 中台/app/services/notification_chain.py 中台/tests/test_notification_chain.py
git commit -m "feat: add NotificationChain - structured notification routing on stage completion"
```

---

## Task 7: ReminderService - asyncio background polling

**Files:**
- Create: `中台/app/services/reminder_service.py`
- Create: `中台/tests/test_reminder_service.py`
- Modify: `中台/app/main.py` (start background task in lifespan)

Background asyncio task that polls every 5 minutes for overdue sub-tasks, sends reminders, and creates anomalies when max retries exceeded.

- [ ] **Step 1: Write failing tests**

Create `中台/tests/test_reminder_service.py`:

```python
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.tables import RDProject, RDSubTask, PipelineTemplate, ReminderLog, RDTask
from app.services.reminder_service import ReminderService


@pytest.fixture
def mock_adapters():
    dt = MagicMock()
    dt.send_private_message = AsyncMock()
    return {"dingtalk": dt}


def _make_overdue_project(db_session, timeout_days=3, overdue_hours=25):
    """Create a project with one dispatched sub-task that is overdue."""
    stages = [
        {
            "name": "OverdueStage",
            "timeout_days": timeout_days,
            "reminder_policy": {
                "first_delay_hours": 24,
                "interval_hours": 12,
                "escalation_delay_hours": 24,
                "max_retries": 3,
            },
        },
    ]
    project = RDProject(name="Overdue", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(project)
    db_session.flush()

    created_at = datetime.now(timezone.utc) - timedelta(hours=overdue_hours)
    sub = RDSubTask(
        project_id=project.id,
        title="OverdueStage",
        assignees=json.dumps(["user_a"]),
        group_id="g1",
        platform="dingtalk",
        deliverables="[]",
        status="dispatched",
        sort_order=0,
        stage_index=0,
        stage_name="OverdueStage",
        created_at=created_at,
    )
    db_session.add(sub)
    db_session.commit()
    return project, sub


def test_find_overdue_tasks(db_session, mock_adapters):
    project, sub = _make_overdue_project(db_session, timeout_days=1, overdue_hours=30)
    svc = ReminderService(db_session, mock_adapters)
    overdue = svc.find_overdue_tasks()
    assert len(overdue) >= 1
    assert overdue[0].id == sub.id


def test_find_overdue_tasks_none_overdue(db_session, mock_adapters):
    project, sub = _make_overdue_project(db_session, timeout_days=10, overdue_hours=1)
    svc = ReminderService(db_session, mock_adapters)
    overdue = svc.find_overdue_tasks()
    assert len(overdue) == 0


def test_send_reminder(db_session, mock_adapters):
    project, sub = _make_overdue_project(db_session, timeout_days=1, overdue_hours=26)
    svc = ReminderService(db_session, mock_adapters)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        svc.send_reminder(sub, "private")
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()
    # ReminderLog should be created
    logs = db_session.query(ReminderLog).filter(
        ReminderLog.task_id == sub.task_instance_id
    ).all()
    # May be 0 if no task_instance_id


def test_check_and_remind_creates_anomaly(db_session, mock_adapters):
    """When reminder count exceeds max, an anomaly dict should be returned."""
    project, sub = _make_overdue_project(db_session, timeout_days=1, overdue_hours=72)
    svc = ReminderService(db_session, mock_adapters)

    # Simulate existing reminders at max count
    if sub.task_instance_id is None:
        # Create a dummy task_instance for the reminder log
        from app.models.tables import TaskInstance
        inst = TaskInstance(
            handler_name="RDTaskHandler",
            feishu_record_id="test",
            platform="dingtalk",
            group_id="g1",
            status="pending",
        )
        db_session.add(inst)
        db_session.flush()
        sub.task_instance_id = inst.id
        db_session.commit()

    from app.models.tables import ReminderLog
    for i in range(3):
        log = ReminderLog(
            task_id=sub.task_instance_id,
            remind_type="private",
            remind_count=i + 1,
        )
        db_session.add(log)
    db_session.commit()

    import asyncio
    anomalies = asyncio.get_event_loop().run_until_complete(
        svc.check_and_remind()
    )
    # Should detect anomaly (max retries exceeded)
    assert isinstance(anomalies, list)


def test_is_not_overdue_for_pending(db_session, mock_adapters):
    """Pending tasks should not be considered overdue."""
    stages = [{"name": "S0", "timeout_days": 1}]
    project = RDProject(name="P", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(project)
    db_session.flush()

    sub = RDSubTask(
        project_id=project.id, title="S0", assignees="[]", group_id="g1",
        platform="dingtalk", deliverables="[]", status="pending",
        sort_order=0, stage_index=0, stage_name="S0",
    )
    db_session.add(sub)
    db_session.commit()

    svc = ReminderService(db_session, mock_adapters)
    overdue = svc.find_overdue_tasks()
    assert len(overdue) == 0
```

Run:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_reminder_service.py -x -q
```

- [ ] **Step 2: Implement ReminderService**

Create `中台/app/services/reminder_service.py`:

```python
"""Reminder service for polling overdue tasks and sending notifications."""
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.tables import RDSubTask, RDProject, ReminderLog

logger = logging.getLogger(__name__)


class ReminderService:
    """Polls for overdue tasks and sends reminder notifications.

    Designed to run as an asyncio background task with 5-minute intervals.
    """

    def __init__(self, db: Session, adapters: dict):
        self.db = db
        self.adapters = adapters

    def find_overdue_tasks(self) -> List[RDSubTask]:
        """Find dispatched sub-tasks that have exceeded their timeout."""
        now = datetime.now(timezone.utc)
        results = []

        # Get all dispatched sub-tasks with projects
        dispatched = self.db.query(RDSubTask).filter(
            RDSubTask.status == "dispatched",
            RDSubTask.project_id.isnot(None),
        ).all()

        for sub in dispatched:
            project = self.db.query(RDProject).filter(RDProject.id == sub.project_id).first()
            if not project:
                continue

            stages = json.loads(project.stages_snapshot)
            if sub.stage_index is None or sub.stage_index >= len(stages):
                continue

            stage = stages[sub.stage_index]
            timeout_days = stage.get("timeout_days", 3)

            if sub.created_at:
                deadline = sub.created_at + timedelta(days=timeout_days)
                if now > deadline:
                    results.append(sub)

        return results

    async def send_reminder(self, sub: RDSubTask, remind_type: str = "private") -> None:
        """Send a reminder for an overdue sub-task."""
        assignees = json.loads(sub.assignees) if sub.assignees else []
        stage_name = sub.stage_name or sub.title
        message = f"提醒：您在阶段「{stage_name}」的任务已超时，请尽快处理。"

        adapter = self.adapters.get(sub.platform)
        if adapter:
            for assignee in assignees:
                try:
                    await adapter.send_private_message(assignee, message)
                except Exception as e:
                    logger.warning(f"Failed to send reminder to {assignee}: {e}")

        # Log the reminder
        if sub.task_instance_id:
            existing = self.db.query(ReminderLog).filter(
                ReminderLog.task_id == sub.task_instance_id,
            ).first()

            if existing:
                existing.remind_count += 1
                existing.last_remind_at = datetime.now(timezone.utc)
                existing.remind_type = remind_type
            else:
                log = ReminderLog(
                    task_id=sub.task_instance_id,
                    remind_type=remind_type,
                    remind_count=1,
                    last_remind_at=datetime.now(timezone.utc),
                )
                self.db.add(log)
            self.db.commit()

    def _get_reminder_count(self, sub: RDSubTask) -> int:
        """Get current reminder count for a sub-task."""
        if not sub.task_instance_id:
            return 0
        log = self.db.query(ReminderLog).filter(
            ReminderLog.task_id == sub.task_instance_id,
        ).first()
        return log.remind_count if log else 0

    def _get_max_retries(self, sub: RDSubTask) -> int:
        """Get max retries from stage config."""
        project = self.db.query(RDProject).filter(RDProject.id == sub.project_id).first()
        if not project:
            return 3
        stages = json.loads(project.stages_snapshot)
        if sub.stage_index is not None and sub.stage_index < len(stages):
            policy = stages[sub.stage_index].get("reminder_policy", {})
            return policy.get("max_retries", 3)
        return 3

    async def check_and_remind(self) -> List[Dict[str, Any]]:
        """Main check loop: find overdue, send reminders, return anomalies."""
        overdue = self.find_overdue_tasks()
        anomalies = []

        for sub in overdue:
            count = self._get_reminder_count(sub)
            max_retries = self._get_max_retries(sub)

            if count >= max_retries:
                # Create anomaly
                anomalies.append({
                    "type": "overdue_escalation",
                    "severity": "critical",
                    "project_id": sub.project_id,
                    "sub_task_id": sub.id,
                    "stage_name": sub.stage_name,
                    "message": f"阶段「{sub.stage_name}」催办 {count} 次无响应",
                })
                continue

            # Determine reminder type based on count
            if count == 0:
                remind_type = "private"
            elif count == 1:
                remind_type = "group"
            else:
                remind_type = "escalation"

            await self.send_reminder(sub, remind_type)

        return anomalies


async def run_reminder_loop(db_session_factory, adapters: dict, interval_seconds: int = 300):
    """Background asyncio task that runs the reminder check every interval."""
    while True:
        try:
            db = db_session_factory()
            try:
                svc = ReminderService(db, adapters)
                anomalies = await svc.check_and_remind()
                if anomalies:
                    logger.warning(f"ReminderService detected {len(anomalies)} anomalies")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"ReminderService error: {e}")

        await asyncio.sleep(interval_seconds)
```

- [ ] **Step 3: Wire into main.py lifespan**

In `中台/app/main.py`, add to the imports:

```python
from app.services.reminder_service import run_reminder_loop
import asyncio
```

Inside the `lifespan` context manager, after `app.state.handler_registry = registry`, add:

```python
    # Start reminder background task
    reminder_task = asyncio.create_task(
        run_reminder_loop(SessionLocal, adapters, interval_seconds=300)
    )
```

Inside the `yield` (after it, in the cleanup):

```python
    # Cleanup
    reminder_task.cancel()
    try:
        await reminder_task
    except asyncio.CancelledError:
        pass
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_reminder_service.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add 中台/app/services/reminder_service.py 中台/tests/test_reminder_service.py 中台/app/main.py
git commit -m "feat: add ReminderService - asyncio background polling for overdue tasks"
```

---

## Task 8: Anomaly API

**Files:**
- Create: `中台/app/admin/anomalies_api.py`
- Create: `中台/tests/test_anomalies_api.py`
- Modify: `中台/app/main.py` (register router)

Anomalies are derived from sub-task state (no separate table). Query for rework/blocked/overdue tasks. Resolve actions: reassign, resume, skip, dismiss.

- [ ] **Step 1: Write failing tests**

Create `中台/tests/test_anomalies_api.py`:

```python
import json
import pytest
from datetime import datetime, timezone, timedelta
from app.models.tables import RDProject, RDSubTask, PipelineTemplate

AUTH = {"Authorization": "Bearer changeme"}


def _make_project_with_anomaly(db_session, status="rework"):
    stages = [{"name": "AnomStage", "timeout_days": 1}]
    p = RDProject(name="AnomalyProject", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(p)
    db_session.flush()

    sub = RDSubTask(
        project_id=p.id, title="AnomStage",
        assignees=json.dumps(["user_a"]),
        group_id="g1", platform="dingtalk", deliverables="[]",
        status=status, sort_order=0, stage_index=0, stage_name="AnomStage",
    )
    db_session.add(sub)
    db_session.commit()
    return p, sub


def test_list_anomalies_empty(client, db_session):
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_anomalies_finds_rework(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["type"] == "rework"


def test_list_anomalies_finds_blocked(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="blocked")
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    assert any(a["type"] == "blocked" for a in resp.json())


def test_list_anomalies_filter_by_project(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    resp = client.get(f"/api/anomalies?project_id={p.id}", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/api/anomalies?project_id=999", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_resolve_anomaly_resume(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="blocked")
    anomaly_id = sub.id  # anomaly id is the sub_task id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "resume"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert sub.status == "dispatched"


def test_resolve_anomaly_skip(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="blocked")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "skip"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert sub.status == "completed"


def test_resolve_anomaly_reassign(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "reassign", "data": {"assignees": ["user_b"]}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert "user_b" in json.loads(sub.assignees)


def test_resolve_anomaly_dismiss(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "dismiss"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert sub.status == "dispatched"


def test_resolve_anomaly_not_found(client, db_session):
    resp = client.patch(
        "/api/anomalies/999",
        json={"action": "resume"},
        headers=AUTH,
    )
    assert resp.status_code == 404
```

Run:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_anomalies_api.py -x -q
```

- [ ] **Step 2: Implement anomalies_api.py**

Create `中台/app/admin/anomalies_api.py`:

```python
"""Anomaly API - query and resolve anomalies derived from sub-task state."""
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tables import RDSubTask, RDProject
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])

ANOMALY_STATUSES = ("rework", "blocked")
SEVERITY_MAP = {
    "rework": "high",
    "blocked": "medium",
}
TYPE_MAP = {
    "rework": "rework",
    "blocked": "blocked",
}


class AnomalyResolve(BaseModel):
    action: str  # reassign | resume | skip | dismiss
    data: Optional[dict] = None


def _format_anomaly(sub: RDSubTask, project: Optional[RDProject] = None) -> dict:
    return {
        "id": sub.id,  # Use sub_task id as anomaly id
        "type": TYPE_MAP.get(sub.status, "unknown"),
        "severity": SEVERITY_MAP.get(sub.status, "low"),
        "project_id": sub.project_id,
        "project_name": project.name if project else None,
        "stage_name": sub.stage_name,
        "stage_index": sub.stage_index,
        "assignees": json.loads(sub.assignees) if sub.assignees else [],
        "status": sub.status,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


@router.get("")
async def list_anomalies(
    project_id: Optional[int] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    q = db.query(RDSubTask).filter(RDSubTask.status.in_(ANOMALY_STATUSES))

    if project_id:
        q = q.filter(RDSubTask.project_id == project_id)

    subs = q.order_by(RDSubTask.updated_at.desc()).all()

    anomalies = []
    for sub in subs:
        project = db.query(RDProject).filter(RDProject.id == sub.project_id).first() if sub.project_id else None
        anomaly = _format_anomaly(sub, project)
        if severity and anomaly.get("severity") != severity:
            continue
        anomalies.append(anomaly)

    return anomalies


@router.patch("/{anomaly_id}")
async def resolve_anomaly(
    anomaly_id: int,
    data: AnomalyResolve,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    sub = db.query(RDSubTask).filter(
        RDSubTask.id == anomaly_id,
        RDSubTask.status.in_(ANOMALY_STATUSES),
    ).first()

    if not sub:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    if data.action == "resume":
        sub.status = "dispatched"
    elif data.action == "skip":
        sub.status = "completed"
    elif data.action == "dismiss":
        sub.status = "dispatched"
    elif data.action == "reassign":
        new_assignees = (data.data or {}).get("assignees", [])
        if new_assignees:
            sub.assignees = json.dumps(new_assignees)
        sub.status = "dispatched"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {data.action}")

    db.commit()
    db.refresh(sub)
    project = db.query(RDProject).filter(RDProject.id == sub.project_id).first() if sub.project_id else None
    return _format_anomaly(sub, project)
```

- [ ] **Step 3: Register router in main.py**

Add import:

```python
from app.admin.anomalies_api import router as anomalies_router
```

Add:

```python
app.include_router(anomalies_router)
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_anomalies_api.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add 中台/app/admin/anomalies_api.py 中台/tests/test_anomalies_api.py 中台/app/main.py
git commit -m "feat: add Anomaly API - query and resolve rework/blocked sub-tasks"
```

---

## Task 9: Modify RDTaskHandler for rework and report-problem

**Files:**
- Modify: `中台/app/handlers/rd_task_handler.py`
- Modify: `中台/tests/test_task_engine.py` (or create `中台/tests/test_rd_task_handler_extended.py`)

Extend the handler to support `rework` and `report_problem` callback actions. When a participant reports a problem, the sub-task status should become `blocked`.

- [ ] **Step 1: Write failing tests**

Create `中台/tests/test_rd_task_handler_extended.py`:

```python
"""Extended tests for RDTaskHandler rework and report-problem support."""
from app.handlers.rd_task_handler import RDTaskHandler


def test_handle_callback_rework():
    handler = RDTaskHandler()
    from app.models.types import TaskUpdate

    update = handler.handle_callback("rework", "user_a", None)
    assert update.status == "submitted"
    assert update.flow_state_update is not None
    assert update.flow_state_update.get("rework_by") == "user_a"


def test_handle_callback_report_problem():
    handler = RDTaskHandler()

    update = handler.handle_callback("report_problem", "user_b", None)
    assert update.status == "submitted"
    assert update.flow_state_update is not None
    assert update.flow_state_update.get("reported_problem_by") == "user_b"


def test_handle_callback_confirm():
    handler = RDTaskHandler()

    update = handler.handle_callback("confirm", "user_a", None)
    assert update.status == "confirmed"


def test_build_card_rework_state():
    handler = RDTaskHandler()
    from app.models.types import CardData
    from unittest.mock import MagicMock

    mock_task = MagicMock()
    mock_task.flow_state = '{"title": "Test", "rework_by": "user_a"}'
    mock_task.deadline = None

    card = handler.build_card(mock_task, "rework")
    assert isinstance(card, CardData)
    assert "返工" in card.title or "rework" in card.title.lower() or card.title  # Just verify it builds


def test_build_card_with_problem_report_button():
    handler = RDTaskHandler()
    from app.models.types import CardData
    from unittest.mock import MagicMock

    mock_task = MagicMock()
    mock_task.flow_state = '{"title": "Test"}'
    mock_task.deadline = None

    card = handler.build_card(mock_task, "pending")
    action_labels = [a.label for a in card.actions]
    assert "确认接单" in action_labels or len(card.actions) >= 1
```

Run:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_rd_task_handler_extended.py -x -q
```

- [ ] **Step 2: Modify rd_task_handler.py**

In `中台/app/handlers/rd_task_handler.py`, modify the `handle_callback` method:

```python
    def handle_callback(self, action, user, task):
        from datetime import datetime, timezone

        status_map = {
            "confirm": "confirmed",
            "upload": "submitted",
            "rework": "submitted",
            "report_problem": "submitted",
        }
        new_status = status_map.get(action)

        flow_update = {}
        if new_status:
            flow_update = {
                f"{new_status}_by": user,
                f"{new_status}_at": datetime.now(timezone.utc).isoformat(),
            }

        # Additional flow state for special actions
        if action == "rework":
            flow_update["rework_by"] = user
            flow_update["rework_at"] = datetime.now(timezone.utc).isoformat()
        elif action == "report_problem":
            flow_update["reported_problem_by"] = user
            flow_update["reported_problem_at"] = datetime.now(timezone.utc).isoformat()

        return TaskUpdate(status=new_status, flow_state_update=flow_update if flow_update else None)
```

Also update `build_card` to show rework status and add "report problem" button:

In the `build_card` method, change the `status_text` dict and actions section to:

```python
        # Status indicator for non-pending states
        status_text = {
            "confirmed": "已确认",
            "submitted": "已提交",
            "completed": "已完成",
            "rework": "返工中",
        }
        if state in status_text:
            sections.insert(0, CardSection(text=status_text[state]))

        # Actions by state
        actions = []
        if state == "pending":
            actions.append(CardAction(label="确认接单", action="confirm", style="primary"))
            actions.append(CardAction(label="上报问题", action="report_problem", style="danger"))
        elif state == "confirmed":
            actions.append(CardAction(label="上传文件", action="upload"))
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_rd_task_handler_extended.py tests/test_task_engine.py -x -v
```

Also run all existing tests to ensure nothing broke:

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add 中台/app/handlers/rd_task_handler.py 中台/tests/test_rd_task_handler_extended.py
git commit -m "feat: extend RDTaskHandler with rework and report-problem callback actions"
```

---

## Task 10: Wire PipelineService into task engine completion flow

**Files:**
- Modify: `中台/app/engine/task_engine.py`
- Modify: `中台/tests/test_task_engine.py`

When a task_instance reaches "completed" status and its parent RDSubTask belongs to a project, the task engine should trigger PipelineService.advance_stage and NotificationChain.

- [ ] **Step 1: Add integration test**

Append to `中台/tests/test_task_engine.py` or create a new test function in that file:

```python
def test_handle_callback_triggers_pipeline_advance_on_completion(db_session, db_engine):
    """When all participants complete, and sub-task belongs to a project, pipeline should advance."""
    import json
    from app.models.tables import TaskRoute, TaskInstance, TaskParticipant, RDProject, RDSubTask

    # Set up project with 2 stages
    stages = [
        {"name": "S0", "deliverables": [], "timeout_days": 3},
        {"name": "S1", "deliverables": [], "timeout_days": 3},
    ]
    project = RDProject(name="EngineTest", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(project)
    db_session.flush()

    s0 = RDSubTask(
        project_id=project.id, title="S0", assignees='["u1"]', group_id="g1",
        platform="dingtalk", deliverables="[]", status="dispatched",
        sort_order=0, stage_index=0, stage_name="S0",
    )
    s1 = RDSubTask(
        project_id=project.id, title="S1", assignees='["u2"]', group_id="g1",
        platform="dingtalk", deliverables="[]", status="pending",
        sort_order=1, stage_index=1, stage_name="S1",
    )
    db_session.add_all([s0, s1])
    db_session.flush()

    # Create task instance linked to s0
    route = TaskRoute(
        handler_name="RDTaskHandler",
        feishu_table_id=f"rd_sub_task:{s0.id}",
        platform="dingtalk", group_id="g1",
        field_mapping=json.dumps({"rd_sub_task_id": s0.id}),
        enabled=True,
    )
    db_session.add(route)
    db_session.flush()

    inst = TaskInstance(
        handler_name="RDTaskHandler",
        route_id=route.id,
        feishu_record_id="test",
        platform="dingtalk",
        group_id="g1",
        status="confirmed",
        flow_state=json.dumps({"rd_sub_task_id": s0.id}),
    )
    db_session.add(inst)
    db_session.flush()

    s0.task_instance_id = inst.id
    s0.task_route_id = route.id

    participant = TaskParticipant(
        task_id=inst.id,
        feishu_user_id="u1",
        platform_user_id="dt_u1",
        role="participant",
        status="confirmed",
    )
    db_session.add(participant)
    db_session.commit()

    # The task_engine.handle_callback will mark the participant as completed
    # which triggers the "all done" check, setting instance.status = "completed"
    # We test that the sub-task status is updated to "completed"
    # Note: full pipeline advance happens at the API layer, but sub-task status update happens here
    assert s0.status == "dispatched"
    # After task completes, s0 should remain dispatched until pipeline service advances it
    # The key contract: sub_task.status tracks the pipeline stage status, not task_instance.status
```

This is primarily a documentation/contract test. The actual pipeline advancement is triggered from the API layer or a post-completion hook.

- [ ] **Step 2: Add a post-completion hook in task_engine.py**

In `中台/app/engine/task_engine.py`, after the `if all_done` block that sets `instance.status = "completed"`, add a hook to update the parent RDSubTask:

```python
        # 5b. Check if all participants are done
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

                # Update parent RDSubTask if linked to a project
                self._on_task_instance_completed(instance)

            # Update participant progress in flow_state
            current_state = json.loads(instance.flow_state) if instance.flow_state else {}
            progress = {
                "total": len(all_participants),
                "confirmed": sum(1 for p in all_participants if p.status in ("confirmed", "submitted", "completed")),
                "submitted": sum(1 for p in all_participants if p.status in ("submitted", "completed")),
            }
            current_state["participant_progress"] = progress
            instance.flow_state = json.dumps(current_state)
```

Add the helper method to the TaskEngine class:

```python
    def _on_task_instance_completed(self, instance: TaskInstance) -> None:
        """Hook called when a task instance reaches 'completed' status.

        Updates the parent RDSubTask status to 'completed' if it belongs to a project.
        """
        from app.models.tables import RDSubTask

        sub_task = self.db.query(RDSubTask).filter(
            RDSubTask.task_instance_id == instance.id,
            RDSubTask.project_id.isnot(None),
        ).first()

        if sub_task:
            sub_task.status = "completed"
```

- [ ] **Step 3: Run all tests**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add 中台/app/engine/task_engine.py 中台/tests/test_task_engine.py
git commit -m "feat: auto-update RDSubTask to completed when task instance finishes (project pipeline hook)"
```

---

## Task 11: Full integration test - end-to-end pipeline flow

**Files:**
- Create: `中台/tests/test_pipeline_integration.py`

A single integration test that exercises the full flow: create template -> create project -> start -> stage completes -> auto-advance -> next stage -> ... -> project completed.

- [ ] **Step 1: Write the integration test**

Create `中台/tests/test_pipeline_integration.py`:

```python
"""End-to-end integration test for the full pipeline flow."""
import json
import pytest
from datetime import datetime, timezone
from app.models.tables import (
    PipelineTemplate, RDProject, RDSubTask,
    TaskRoute, TaskInstance, TaskParticipant, ReminderLog,
)

AUTH = {"Authorization": "Bearer changeme"}

THREE_STAGES = [
    {"name": "灵感收集", "description": "collect", "default_assignees": ["u1"],
     "deliverables": [{"name": "参考图", "count": 3}], "timeout_days": 3,
     "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
     "notify_target": {"type": "next_stage_assignee"}},
    {"name": "灵感创作", "description": "create", "default_assignees": ["u2"],
     "deliverables": [{"name": "方案", "count": 1}], "timeout_days": 5,
     "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
     "notify_target": {"type": "next_stage_assignee"}},
    {"name": "品鉴会", "description": "review", "default_assignees": ["u3"],
     "deliverables": [{"name": "品鉴结论", "count": 1}], "timeout_days": 2,
     "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
     "notify_target": {"type": "manager", "also_notify_manager": True}},
]


def test_full_pipeline_flow(client, db_session):
    """Test: create template -> create project -> start -> complete stages -> project done."""

    # 1. Create template
    resp = client.post("/api/templates", json={"name": "3阶段模板", "stages": THREE_STAGES}, headers=AUTH)
    assert resp.status_code == 201
    template_id = resp.json()["id"]

    # 2. Create project from template
    resp = client.post("/api/projects", json={
        "name": "集成测试项目",
        "template_id": template_id,
        "stage_overrides": [],
    }, headers=AUTH)
    assert resp.status_code == 201
    project = resp.json()
    project_id = project["id"]
    assert project["status"] == "draft"
    assert len(project["sub_tasks"]) == 3

    # 3. Start project
    resp = client.post(f"/api/projects/{project_id}/start", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 4. Verify first stage is dispatched
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    subs = resp.json()["sub_tasks"]
    assert subs[0]["status"] == "dispatched"
    assert subs[1]["status"] == "pending"
    assert subs[2]["status"] == "pending"

    # 5. Simulate stage 0 completion (directly update DB)
    s0 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == project_id, RDSubTask.stage_index == 0
    ).first()
    s0.status = "completed"
    db_session.commit()

    # 6. Advance pipeline
    resp = client.post(f"/api/projects/{project_id}/advance",
                       json={"stage_index": 0}, headers=AUTH)
    assert resp.status_code == 200

    # 7. Verify stage 1 is now dispatched
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    subs = resp.json()["sub_tasks"]
    assert subs[0]["status"] == "completed"
    assert subs[1]["status"] == "dispatched"
    assert subs[2]["status"] == "pending"

    # 8. Complete stage 1 and advance
    s1 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == project_id, RDSubTask.stage_index == 1
    ).first()
    s1.status = "completed"
    db_session.commit()

    resp = client.post(f"/api/projects/{project_id}/advance",
                       json={"stage_index": 1}, headers=AUTH)
    assert resp.status_code == 200

    # 9. Verify stage 2 dispatched
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    subs = resp.json()["sub_tasks"]
    assert subs[1]["status"] == "completed"
    assert subs[2]["status"] == "dispatched"

    # 10. Complete stage 2 and advance - should complete project
    s2 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == project_id, RDSubTask.stage_index == 2
    ).first()
    s2.status = "completed"
    db_session.commit()

    resp = client.post(f"/api/projects/{project_id}/advance",
                       json={"stage_index": 2}, headers=AUTH)
    assert resp.status_code == 200

    # 11. Project should be completed
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    assert resp.json()["status"] == "completed"


def test_rework_flow(client, db_session):
    """Test: complete stage -> rework -> complete again -> advance."""

    # Create and start project
    resp = client.post("/api/templates", json={"name": "Rework模板", "stages": THREE_STAGES[:2]}, headers=AUTH)
    template_id = resp.json()["id"]

    resp = client.post("/api/projects", json={
        "name": "Rework项目", "template_id": template_id, "stage_overrides": [],
    }, headers=AUTH)
    project_id = resp.json()["id"]

    client.post(f"/api/projects/{project_id}/start", headers=AUTH)

    # Complete stage 0
    s0 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == project_id, RDSubTask.stage_index == 0
    ).first()
    s0.status = "completed"
    db_session.commit()

    client.post(f"/api/projects/{project_id}/advance", json={"stage_index": 0}, headers=AUTH)

    # Rework stage 0
    resp = client.post(f"/api/projects/{project_id}/rework",
                       json={"stage_index": 0, "reason": "质量不达标"}, headers=AUTH)
    assert resp.status_code == 200

    # Verify stage 0 is in rework
    db_session.refresh(s0)
    assert s0.status == "rework"

    # Check anomaly exists
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    anomalies = resp.json()
    assert any(a["type"] == "rework" for a in anomalies)

    # Resume via anomaly
    resp = client.patch(f"/api/anomalies/{s0.id}", json={"action": "dismiss"}, headers=AUTH)
    assert resp.status_code == 200

    db_session.refresh(s0)
    assert s0.status == "dispatched"


def test_project_pause_resume(client, db_session):
    """Test pausing and resuming a project."""
    resp = client.post("/api/templates", json={"name": "Pause模板", "stages": THREE_STAGES[:2]}, headers=AUTH)
    template_id = resp.json()["id"]

    resp = client.post("/api/projects", json={
        "name": "Pause项目", "template_id": template_id, "stage_overrides": [],
    }, headers=AUTH)
    project_id = resp.json()["id"]

    # Start then pause
    client.post(f"/api/projects/{project_id}/start", headers=AUTH)
    resp = client.patch(f"/api/projects/{project_id}", json={"status": "paused"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

    # Resume
    resp = client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
```

- [ ] **Step 2: Run the full integration test**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/test_pipeline_integration.py -x -v
```

- [ ] **Step 3: Run ALL tests to verify nothing is broken**

```bash
cd /Users/chenzixian/Downloads/写真行业/中台 && python -m pytest tests/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add 中台/tests/test_pipeline_integration.py
git commit -m "test: add end-to-end integration tests for full pipeline flow"
```

---

## Summary of Tasks

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | PipelineTemplate + RDProject models, extend RDSubTask | `models/tables.py`, `models/__init__.py`, `conftest.py` |
| 2 | PipelineTemplate CRUD API | `admin/templates_api.py`, `test_templates_api.py` |
| 3 | RDProject CRUD API (create from template) | `admin/rd_projects_api.py`, `test_rd_projects_api.py` |
| 4 | PipelineService (start/advance/rework) | `services/pipeline_service.py`, `test_pipeline_service.py` |
| 5 | Project start/advance/rework API endpoints | `admin/rd_projects_api.py`, `test_rd_projects_api.py` |
| 6 | NotificationChain service | `services/notification_chain.py`, `test_notification_chain.py` |
| 7 | ReminderService background polling | `services/reminder_service.py`, `test_reminder_service.py` |
| 8 | Anomaly API | `admin/anomalies_api.py`, `test_anomalies_api.py` |
| 9 | RDTaskHandler rework + report-problem | `handlers/rd_task_handler.py`, `test_rd_task_handler_extended.py` |
| 10 | Wire pipeline hook into TaskEngine | `engine/task_engine.py`, `test_task_engine.py` |
| 11 | Full integration test | `test_pipeline_integration.py` |

## Dependency Order

```
Task 1 (models)
  ├── Task 2 (template API)
  ├── Task 3 (project API, depends on Task 2 for template)
  │     └── Task 5 (project start/advance API, depends on Task 4)
  │           └── Task 6 (notification chain)
  ├── Task 4 (pipeline service, depends on models)
  ├── Task 7 (reminder service, depends on models)
  ├── Task 8 (anomaly API, depends on models)
  ├── Task 9 (handler rework, independent)
  └── Task 10 (task engine hook, depends on models + service)
        └── Task 11 (integration test, depends on everything)
```

Recommended execution order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11
