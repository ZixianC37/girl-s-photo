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
        "id": sub.id,
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
