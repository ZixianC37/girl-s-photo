from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.tables import TaskInstance, TaskParticipant
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    handler: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """List task instances with optional filtering by status and handler."""
    query = db.query(TaskInstance)

    if status:
        query = query.filter(TaskInstance.status == status)

    if handler:
        query = query.filter(TaskInstance.handler_name == handler)

    total = query.count()

    # Calculate pagination
    offset = (page - 1) * page_size
    tasks = query.order_by(TaskInstance.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": t.id,
                "handler_name": t.handler_name,
                "feishu_record_id": t.feishu_record_id,
                "platform": t.platform,
                "group_id": t.group_id,
                "status": t.status,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tasks
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """Get detailed information about a specific task including participants."""
    task = db.query(TaskInstance).filter(TaskInstance.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get participants for this task
    participants = db.query(TaskParticipant).filter(TaskParticipant.task_id == task_id).all()

    return {
        "id": task.id,
        "handler_name": task.handler_name,
        "route_id": task.route_id,
        "feishu_record_id": task.feishu_record_id,
        "platform": task.platform,
        "group_id": task.group_id,
        "card_id": task.card_id,
        "status": task.status,
        "flow_state": task.flow_state,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "participants": [
            {
                "id": p.id,
                "feishu_user_id": p.feishu_user_id,
                "platform_user_id": p.platform_user_id,
                "role": p.role,
                "status": p.status,
                "file_count": p.file_count,
                "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in participants
        ]
    }
