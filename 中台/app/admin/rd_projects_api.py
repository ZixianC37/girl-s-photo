import json
from typing import Optional, List, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tables import PipelineTemplate, RDProject, RDSubTask, TaskRoute
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ---------- Helpers (engine dispatch) ----------

async def _dispatch_sub_task_via_engine(sub: RDSubTask, db: Session, task_engine) -> None:
    """Dispatch a sub-task through the TaskEngine."""
    import json as _json
    route = TaskRoute(
        handler_name="RDTaskHandler",
        feishu_table_id=f"rd_sub_task:{sub.id}",
        platform=sub.platform or "dingtalk",
        group_id=sub.group_id or "",
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
        pass


# ---------- Request / Response models ----------

class StageOverride(BaseModel):
    assignees: Optional[List[str]] = None
    deadline: Optional[str] = None
    group_id: Optional[str] = None
    platform: Optional[str] = None
    deliverables: Optional[list] = None


class SubTaskInput(BaseModel):
    title: str
    description: str = ""
    assignees: List[str] = []
    deliverable_rules: List[dict] = []
    reminder_config: Optional[dict] = None


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    template_id: Optional[int] = None
    sub_tasks: Optional[List[SubTaskInput]] = None
    stage_overrides: Optional[Dict[str, StageOverride]] = None


class ProjectStatusUpdate(BaseModel):
    status: str  # "active" | "paused" | "draft" | "completed"


class AdvanceRequest(BaseModel):
    stage_index: Optional[int] = None


class ReworkRequest(BaseModel):
    stage_index: int
    reason: str = ""


# ---------- Helpers ----------

def _format_sub_task(st: RDSubTask) -> dict:
    return {
        "id": st.id,
        "project_id": st.project_id,
        "stage_index": st.stage_index,
        "stage_name": st.stage_name,
        "rd_task_id": st.rd_task_id,
        "title": st.title,
        "description": st.description,
        "assignees": st.assignees,
        "group_id": st.group_id,
        "platform": st.platform,
        "deadline": st.deadline.isoformat() if st.deadline else None,
        "deliverables": st.deliverables,
        "status": st.status,
        "sort_order": st.sort_order,
        "created_at": st.created_at.isoformat() if st.created_at else None,
        "updated_at": st.updated_at.isoformat() if st.updated_at else None,
    }


def _format_project(p: RDProject, include_sub_tasks: bool = False) -> dict:
    result = {
        "id": p.id,
        "name": p.name,
        "description": p.description or "",
        "template_id": p.template_id,
        "stages_snapshot": p.stages_snapshot,
        "status": p.status,
        "created_by": p.created_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
    if include_sub_tasks:
        result["sub_tasks"] = [_format_sub_task(st) for st in p.sub_tasks]
    return result


# ---------- Endpoints ----------

@router.post("", status_code=201)
async def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    # Determine sub-task definitions: from direct input or from template
    sub_task_defs = []
    template_id = data.template_id
    stages_snapshot = "[]"

    if data.sub_tasks:
        # Direct sub-tasks from request
        sub_task_defs = [s.model_dump() for s in data.sub_tasks]
    elif data.template_id:
        # From template (backward compatible)
        template = db.query(PipelineTemplate).filter(PipelineTemplate.id == data.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        from app.admin.templates_api import _migrate_stages
        stages_raw = json.loads(template.stages) if template.stages else []
        sub_task_defs = _migrate_stages(stages_raw)
        template_id = template.id
        stages_snapshot = template.stages
    else:
        raise HTTPException(status_code=400, detail="Must provide sub_tasks or template_id")

    project = RDProject(
        name=data.name,
        description=data.description,
        template_id=template_id,
        stages_snapshot=stages_snapshot,
        status="draft",
    )
    db.add(project)
    db.flush()

    for idx, sub_def in enumerate(sub_task_defs):
        overrides = None
        if data.stage_overrides and str(idx) in data.stage_overrides:
            overrides = data.stage_overrides[str(idx)]

        assignees = json.dumps(sub_def.get("assignees", []))
        deliverables = json.dumps(sub_def.get("deliverable_rules", []))
        deadline = None
        group_id = ""
        platform = ""

        if overrides:
            if overrides.assignees is not None:
                assignees = json.dumps(overrides.assignees)
            if overrides.deadline is not None:
                try:
                    deadline = datetime.fromisoformat(overrides.deadline.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            if overrides.group_id is not None:
                group_id = overrides.group_id
            if overrides.platform is not None:
                platform = overrides.platform
            if overrides.deliverables is not None:
                deliverables = json.dumps(overrides.deliverables)

        sub_task = RDSubTask(
            project_id=project.id,
            stage_index=idx,
            stage_name=sub_def.get("title", f"子任务 {idx+1}"),
            title=sub_def.get("title", f"子任务 {idx+1}"),
            description=sub_def.get("description", ""),
            assignees=assignees,
            group_id=group_id,
            platform=platform,
            deadline=deadline,
            deliverables=deliverables,
            status="pending",
            sort_order=idx,
        )
        db.add(sub_task)

    db.commit()
    db.refresh(project)
    return _format_project(project, include_sub_tasks=True)


@router.get("")
async def list_projects(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    query = db.query(RDProject)
    if status:
        query = query.filter(RDProject.status == status)
    projects = query.order_by(RDProject.id.desc()).all()
    return [_format_project(p, include_sub_tasks=False) for p in projects]


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    project = db.query(RDProject).filter(RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _format_project(project, include_sub_tasks=True)


@router.patch("/{project_id}")
async def update_project_status(
    project_id: int,
    data: ProjectStatusUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    project = db.query(RDProject).filter(RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # TODO (Task 5): When status changes to "active", wire to PipelineService
    project.status = data.status
    db.commit()
    db.refresh(project)
    return _format_project(project, include_sub_tasks=True)


@router.post("/{project_id}/start")
async def start_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = getattr(request.app.state, 'task_engine', None)
    svc = PipelineService(db, engine)
    result = svc.start_project(project_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot start project (must be in draft status)")

    db_obj = db.query(RDProject).filter(RDProject.id == project_id).first()
    first_sub = db.query(RDSubTask).filter(
        RDSubTask.project_id == project_id,
        RDSubTask.stage_index == 0,
    ).first()
    if first_sub and engine:
        await _dispatch_sub_task_via_engine(first_sub, db, engine)

    return _format_project(db_obj, include_sub_tasks=True)


@router.post("/{project_id}/advance")
async def advance_project(
    project_id: int,
    data: AdvanceRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = getattr(request.app.state, 'task_engine', None)

    # If stage_index provided, mark as completed first
    if data.stage_index is not None:
        sub_task = db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == data.stage_index,
        ).first()
        if sub_task:
            sub_task.status = "completed"
            db.commit()

    svc = PipelineService(db, engine)
    result = svc.advance_project_stage(project_id, data.stage_index or 0)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot advance (stage not completed or project not active)")

    db_obj = db.query(RDProject).filter(RDProject.id == project_id).first()
    return _format_project(db_obj, include_sub_tasks=True)


@router.post("/{project_id}/rework")
async def rework_stage(
    project_id: int,
    data: ReworkRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = getattr(request.app.state, 'task_engine', None)
    svc = PipelineService(db, engine)
    result = svc.rework_project_stage(project_id, data.stage_index, data.reason)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot rework (stage must be completed or dispatched)")

    db_obj = db.query(RDProject).filter(RDProject.id == project_id).first()
    return _format_project(db_obj, include_sub_tasks=True)


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    project = db.query(RDProject).filter(RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Cascade delete handled by ORM relationship (delete-orphan)
    db.delete(project)
    db.commit()
    return {"status": "deleted"}
