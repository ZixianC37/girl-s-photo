"""Pipeline service for managing RDTask stage advancement."""
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.tables import RDTask, RDSubTask


class PipelineService:
    """Orchestrates pipeline stage transitions for RDTask."""

    def __init__(self, db: Session, task_engine=None):
        self.db = db
        self.task_engine = task_engine

    def start_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Start a draft RDTask by dispatching the first stage."""
        task = self.db.query(RDTask).filter(RDTask.id == task_id).first()
        if not task or task.status != "draft":
            return None

        task.status = "active"
        self.db.flush()

        first_sub = self.db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id,
            RDSubTask.sort_order == 0,
        ).first()

        if first_sub:
            first_sub.status = "dispatched"

        self.db.commit()
        self.db.refresh(task)
        return {"id": task.id, "title": task.title, "status": task.status}

    def advance_stage(self, task_id: int, stage_index: int) -> Optional[Dict[str, Any]]:
        """Advance pipeline after a stage completes."""
        task = self.db.query(RDTask).filter(RDTask.id == task_id).first()
        if not task or task.status != "active":
            return None

        current_sub = self.db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id,
            RDSubTask.sort_order == stage_index,
        ).first()

        if not current_sub or current_sub.status != "completed":
            return None

        next_sub = self.db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id,
            RDSubTask.sort_order == stage_index + 1,
        ).first()

        if next_sub:
            next_sub.status = "dispatched"
        else:
            task.status = "completed"

        self.db.commit()
        self.db.refresh(task)
        return {"id": task.id, "title": task.title, "status": task.status}

    def rework_stage(self, task_id: int, stage_index: int, reason: str = "") -> Optional[Dict[str, Any]]:
        """Put a stage into rework status."""
        sub = self.db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id,
            RDSubTask.sort_order == stage_index,
        ).first()

        if not sub or sub.status not in ("completed", "dispatched"):
            return None

        sub.status = "rework"
        self.db.commit()
        self.db.refresh(sub)
        return {"id": sub.id, "title": sub.title, "status": sub.status, "sort_order": sub.sort_order}

    def start_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Start a draft RDProject by dispatching the first stage."""
        from app.models.tables import RDProject
        project = self.db.query(RDProject).filter(RDProject.id == project_id).first()
        if not project or project.status != "draft":
            return None

        project.status = "active"
        self.db.flush()

        first_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == 0,
        ).first()

        if first_sub:
            first_sub.status = "dispatched"

        self.db.commit()
        self.db.refresh(project)
        return {"id": project.id, "name": project.name, "status": project.status}

    def advance_project_stage(self, project_id: int, stage_index: int) -> Optional[Dict[str, Any]]:
        """Advance project pipeline after a stage completes."""
        from app.models.tables import RDProject
        project = self.db.query(RDProject).filter(RDProject.id == project_id).first()
        if not project or project.status != "active":
            return None

        current_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == stage_index,
        ).first()

        if not current_sub or current_sub.status != "completed":
            return None

        next_sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == stage_index + 1,
        ).first()

        if next_sub:
            next_sub.status = "dispatched"
        else:
            project.status = "completed"

        self.db.commit()
        self.db.refresh(project)
        return {"id": project.id, "name": project.name, "status": project.status}

    def rework_project_stage(self, project_id: int, stage_index: int, reason: str = "") -> Optional[Dict[str, Any]]:
        """Put a project stage into rework status."""
        sub = self.db.query(RDSubTask).filter(
            RDSubTask.project_id == project_id,
            RDSubTask.stage_index == stage_index,
        ).first()

        if not sub or sub.status not in ("completed", "dispatched"):
            return None

        sub.status = "rework"
        self.db.commit()
        self.db.refresh(sub)
        return {"id": sub.id, "title": sub.title, "status": sub.status, "stage_index": sub.stage_index}

    def get_active_stages(self, task_id: int) -> List[RDSubTask]:
        """Get currently active (dispatched/rework/blocked) stages."""
        return self.db.query(RDSubTask).filter(
            RDSubTask.rd_task_id == task_id,
            RDSubTask.status.in_(["dispatched", "rework", "blocked"]),
        ).order_by(RDSubTask.sort_order).all()
