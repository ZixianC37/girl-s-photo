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
    """Polls for overdue tasks and sends reminder notifications."""

    def __init__(self, db: Session, adapters: dict):
        self.db = db
        self.adapters = adapters

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Add UTC timezone info if the datetime is naive."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def find_overdue_tasks(self) -> List[RDSubTask]:
        """Find dispatched sub-tasks that have exceeded their timeout."""
        now = datetime.now(timezone.utc)
        results = []

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
                deadline = self._ensure_aware(sub.created_at) + timedelta(days=timeout_days)
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
        if not sub.task_instance_id:
            return 0
        log = self.db.query(ReminderLog).filter(
            ReminderLog.task_id == sub.task_instance_id,
        ).first()
        return log.remind_count if log else 0

    def _get_max_retries(self, sub: RDSubTask) -> int:
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
                anomalies.append({
                    "type": "overdue_escalation",
                    "severity": "critical",
                    "project_id": sub.project_id,
                    "sub_task_id": sub.id,
                    "stage_name": sub.stage_name,
                    "message": f"阶段「{sub.stage_name}」催办 {count} 次无响应",
                })
                continue

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
