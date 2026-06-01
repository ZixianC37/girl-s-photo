import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from app.database import get_db
from app.models.tables import PipelineTemplate, RDProject
from app.admin.auth import verify_admin

router = APIRouter(prefix="/api/templates", tags=["templates"])


# --- New SubTaskDef-based models ---

class DeliverableCollectionRule(BaseModel):
    name: str
    format: str = "image"  # image / video / document / any
    required_count: int = 1
    description: str = ""


class ReminderConfig(BaseModel):
    first_delay_hours: int = 24
    interval_hours: int = 12
    escalation_delay_hours: int = 24
    max_retries: int = 3


class SubTaskDef(BaseModel):
    title: str
    description: str = ""
    assignees: List[str] = []
    deliverable_rules: List[DeliverableCollectionRule] = []
    reminder_config: Optional[ReminderConfig] = None


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    sub_tasks: List[SubTaskDef]

    @field_validator("sub_tasks")
    @classmethod
    def validate_sub_tasks_length(cls, v: List[SubTaskDef]) -> List[SubTaskDef]:
        if len(v) < 1 or len(v) > 20:
            raise ValueError("sub_tasks must contain between 1 and 20 items")
        return v


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sub_tasks: Optional[List[SubTaskDef]] = None

    @field_validator("sub_tasks")
    @classmethod
    def validate_sub_tasks_length(cls, v: Optional[List[SubTaskDef]]) -> Optional[List[SubTaskDef]]:
        if v is not None and (len(v) < 1 or len(v) > 20):
            raise ValueError("sub_tasks must contain between 1 and 20 items")
        return v


# --- Backward compatibility: auto-migrate old StageSpec format ---

def _migrate_stages(raw: list) -> list:
    """Convert old StageSpec format to new SubTaskDef format on read."""
    result = []
    for item in raw:
        if isinstance(item, dict):
            if "name" in item and "default_assignees" in item:
                # Old StageSpec format → convert
                result.append({
                    "title": item["name"],
                    "description": item.get("description", ""),
                    "assignees": item.get("default_assignees", []),
                    "deliverable_rules": [
                        {"name": d.get("name", ""), "format": "image", "required_count": d.get("count", 1)}
                        for d in item.get("deliverables", [])
                        if isinstance(d, dict)
                    ],
                    "reminder_config": {
                        "first_delay_hours": (item.get("reminder_policy") or {}).get("first_delay_hours", 24),
                        "interval_hours": (item.get("reminder_policy") or {}).get("interval_hours", 12),
                    } if item.get("reminder_policy") else None,
                })
            else:
                # Already new format
                result.append(item)
    return result


def _format_template(t: PipelineTemplate) -> dict:
    raw = json.loads(t.stages) if t.stages else []
    migrated = _migrate_stages(raw)
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description or "",
        "sub_tasks": migrated,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("")
async def list_templates(
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    templates = db.query(PipelineTemplate).all()
    return [_format_template(t) for t in templates]


@router.post("", status_code=201)
async def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    sub_tasks_json = json.dumps([s.model_dump() for s in data.sub_tasks])
    t = PipelineTemplate(
        name=data.name,
        description=data.description,
        stages=sub_tasks_json,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _format_template(t)


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
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
    if data.sub_tasks is not None:
        t.stages = json.dumps([s.model_dump() for s in data.sub_tasks])

    db.commit()
    db.refresh(t)
    return _format_template(t)


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
    t = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    active_count = db.query(RDProject).filter(
        RDProject.template_id == template_id,
        RDProject.status.in_(["active", "draft"]),
    ).count()
    if active_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {active_count} active/draft project(s) use this template",
        )

    db.delete(t)
    db.commit()
    return {"status": "deleted"}


@router.post("/{template_id}/clone", status_code=201)
async def clone_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin),
):
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
