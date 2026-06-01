from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.tables import (
    TaskRoute, TaskInstance, TaskParticipant, FileRecord, ReminderLog, RDTask, RDSubTask, PipelineTemplate
)
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api", tags=["admin"])


class DeliverableSpec(BaseModel):
    name: str
    type: str = "image"
    count: int = 1


class SubTaskCreate(BaseModel):
    title: str
    description: str = ""
    assignees: List[str]
    group_id: str
    platform: str
    deadline: Optional[str] = None
    deliverables: List[DeliverableSpec] = []
    sort_order: int = 0


class RDTaskCreate(BaseModel):
    title: str
    description: str = ""
    sub_tasks: List[SubTaskCreate] = []
    template_id: Optional[int] = None
    stage_overrides: Optional[dict] = None  # {stage_index: {assignees, deadline, ...}}


def parse_datetime(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except:
        return None


def _format_rd_task(rd_task: RDTask, db: Session) -> dict:
    import json

    sub_tasks_data = []
    for sub in rd_task.sub_tasks:
        # Get progress if task_instance exists
        progress = None
        participant_count = 0
        completed_count = 0

        if sub.task_instance_id:
            participant_count = db.query(TaskParticipant).filter(
                TaskParticipant.task_id == sub.task_instance_id
            ).count()
            completed_count = db.query(TaskParticipant).filter(
                TaskParticipant.task_id == sub.task_instance_id,
                TaskParticipant.status == "completed"
            ).count()

            if participant_count > 0:
                progress = f"{completed_count}/{participant_count}"

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
            "task_instance_id": sub.task_instance_id,
            "task_route_id": sub.task_route_id,
            "sort_order": sub.sort_order,
            "progress": progress,
        })

    return {
        "id": rd_task.id,
        "title": rd_task.title,
        "description": rd_task.description,
        "status": rd_task.status,
        "created_by": rd_task.created_by,
        "template_id": rd_task.template_id,
        "stages_snapshot": rd_task.stages_snapshot,
        "created_at": rd_task.created_at.isoformat() if rd_task.created_at else None,
        "updated_at": rd_task.updated_at.isoformat() if rd_task.updated_at else None,
        "sub_tasks": sub_tasks_data,
    }


@router.get("/rd-tasks")
async def list_rd_tasks(db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    rd_tasks = db.query(RDTask).all()
    return [
        {
            "id": rd.id,
            "title": rd.title,
            "description": rd.description,
            "status": rd.status,
            "created_at": rd.created_at.isoformat() if rd.created_at else None,
            "sub_task_count": len(rd.sub_tasks),
        }
        for rd in rd_tasks
    ]


@router.post("/rd-tasks", status_code=201)
async def create_rd_task(
    data: RDTaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    import json

    # If template_id provided, generate sub_tasks from template
    if data.template_id and not data.sub_tasks:
        from app.admin.templates_api import _migrate_stages
        template = db.query(PipelineTemplate).filter(PipelineTemplate.id == data.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        raw = json.loads(template.stages) if template.stages else []
        sub_task_defs = _migrate_stages(raw)
        overrides = data.stage_overrides or {}

        rd_task = RDTask(
            title=data.title,
            description=data.description,
            status="draft",
            template_id=template.id,
            stages_snapshot=template.stages,
        )
        db.add(rd_task)
        db.flush()

        for idx, sub_def in enumerate(sub_task_defs):
            override = overrides.get(str(idx), {})
            sub = RDSubTask(
                rd_task_id=rd_task.id,
                title=sub_def.get("title", f"子任务 {idx+1}"),
                description=sub_def.get("description", ""),
                assignees=json.dumps(override.get("assignees", sub_def.get("assignees", []))),
                group_id=override.get("group_id", ""),
                platform=override.get("platform", "dingtalk"),
                deadline=parse_datetime(override["deadline"]) if override.get("deadline") else None,
                deliverables=json.dumps(sub_def.get("deliverable_rules", [])),
                sort_order=idx,
                stage_index=idx,
                stage_name=sub_def.get("title", f"子任务 {idx+1}"),
                status="pending",
            )
            db.add(sub)
    else:
        # Manual sub_tasks (backward compatible)
        rd_task = RDTask(title=data.title, description=data.description, status="active")
        db.add(rd_task)
        db.flush()

        task_engine = request.app.state.task_engine

        for st in data.sub_tasks:
            sub = RDSubTask(
                rd_task_id=rd_task.id,
                title=st.title,
                description=st.description,
                assignees=json.dumps(st.assignees),
                group_id=st.group_id,
                platform=st.platform,
                deadline=parse_datetime(st.deadline) if st.deadline else None,
                deliverables=json.dumps([d.model_dump() for d in st.deliverables]),
                sort_order=st.sort_order,
                stage_index=st.sort_order,
                stage_name=st.title,
            )
            db.add(sub)
            db.flush()

            route = TaskRoute(
                handler_name="RDTaskHandler",
                feishu_table_id=f"rd_sub_task:{sub.id}",
                platform=sub.platform,
                group_id=sub.group_id,
                field_mapping=json.dumps({
                    "rd_sub_task_id": sub.id,
                    "title": sub.title,
                    "assignees": st.assignees,
                    "deliverables": [d.model_dump() for d in st.deliverables],
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
                    sub.status = "dispatched"
            except Exception:
                sub.status = "pending"

    db.commit()
    db.refresh(rd_task)
    return _format_rd_task(rd_task, db)


@router.get("/rd-tasks/{task_id}")
async def get_rd_task(task_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin)):
    rd = db.query(RDTask).filter(RDTask.id == task_id).first()
    if not rd:
        raise HTTPException(status_code=404, detail="RD task not found")
    return _format_rd_task(rd, db)


@router.delete("/rd-tasks/{task_id}")
async def delete_rd_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    rd = db.query(RDTask).filter(RDTask.id == task_id).first()
    if not rd:
        raise HTTPException(status_code=404, detail="RD task not found")

    for sub in rd.sub_tasks:
        if sub.task_instance_id:
            # Delete cascade
            db.query(FileRecord).filter(FileRecord.task_id == sub.task_instance_id).delete()
            db.query(ReminderLog).filter(ReminderLog.task_id == sub.task_instance_id).delete()
            db.query(TaskParticipant).filter(TaskParticipant.task_id == sub.task_instance_id).delete()
            db.query(TaskInstance).filter(TaskInstance.id == sub.task_instance_id).delete()
        if sub.task_route_id:
            db.query(TaskRoute).filter(TaskRoute.id == sub.task_route_id).delete()

    db.delete(rd)  # CASCADE deletes rd_sub_task
    db.commit()
    return {"status": "deleted"}


# --- Pipeline operations on RDTask ---

@router.post("/rd-tasks/{task_id}/start")
async def start_rd_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = getattr(request.app.state, 'task_engine', None)
    svc = PipelineService(db, engine)
    result = svc.start_task(task_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot start (must be in draft status)")

    # Dispatch first sub-task via task engine
    if engine:
        first_sub = db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id, RDSubTask.sort_order == 0
        ).first()
        if first_sub:
            await _dispatch_sub(first_sub, db, engine)

    rd = db.query(RDTask).filter(RDTask.id == task_id).first()
    return _format_rd_task(rd, db)


@router.post("/rd-tasks/{task_id}/advance")
async def advance_rd_task(
    task_id: int,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    stage_index = data.get("stage_index", 0)

    # Mark stage as completed
    sub = db.query(RDSubTask).filter(
        RDSubTask.rd_task_id == task_id, RDSubTask.sort_order == stage_index
    ).first()
    if sub:
        sub.status = "completed"
        db.commit()

    engine = getattr(request.app.state, 'task_engine', None)
    svc = PipelineService(db, engine)
    result = svc.advance_stage(task_id, stage_index)
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot advance")

    # Dispatch next sub-task if exists
    if engine and result["status"] == "active":
        next_sub = db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id, RDSubTask.sort_order == stage_index + 1
        ).first()
        if next_sub:
            await _dispatch_sub(next_sub, db, engine)

    rd = db.query(RDTask).filter(RDTask.id == task_id).first()
    return _format_rd_task(rd, db)


@router.post("/rd-tasks/{task_id}/rework")
async def rework_rd_task_stage(
    task_id: int,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    from app.services.pipeline_service import PipelineService
    engine = getattr(request.app.state, 'task_engine', None)
    svc = PipelineService(db, engine)
    result = svc.rework_stage(task_id, data.get("stage_index", 0), data.get("reason", ""))
    if result is None:
        raise HTTPException(status_code=400, detail="Cannot rework (stage must be completed or dispatched)")

    rd = db.query(RDTask).filter(RDTask.id == task_id).first()
    return _format_rd_task(rd, db)


async def _dispatch_sub(sub: RDSubTask, db: Session, task_engine) -> None:
    """Dispatch a sub-task through TaskEngine."""
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
