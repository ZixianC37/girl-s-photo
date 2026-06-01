from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.tables import TaskRoute, TaskInstance
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """Get dashboard statistics including active routes, handlers, and task metrics."""

    # Count active routes
    active_routes = db.query(TaskRoute).filter(TaskRoute.enabled == True).count()

    # Get registered handlers from app.state
    registry = getattr(request.app.state, "handler_registry", None)
    registered_handlers = len(registry.list_handlers()) if registry else 0

    # Count today's tasks (SQLite date function)
    today_tasks = db.query(TaskInstance).filter(
        func.date(TaskInstance.created_at) == func.date('now')
    ).count()

    # Calculate error rate
    from sqlalchemy import cast, case, Float
    error_rate_result = db.query(
        cast(
            func.sum(case((TaskInstance.status == 'error', 1), else_=0)),
            Float
        ) / func.nullif(func.count(TaskInstance.id), 0)
    ).scalar()
    error_rate = float(error_rate_result) if error_rate_result is not None else 0.0

    # Get recent tasks
    recent_tasks = db.query(TaskInstance).order_by(
        TaskInstance.created_at.desc()
    ).limit(10).all()

    recent_tasks_data = [
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
        for t in recent_tasks
    ]

    return {
        "active_routes": active_routes,
        "registered_handlers": registered_handlers,
        "today_tasks": today_tasks,
        "error_rate": error_rate,
        "recent_tasks": recent_tasks_data,
    }
