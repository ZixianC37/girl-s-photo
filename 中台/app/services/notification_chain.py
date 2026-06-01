"""Notification chain service for pipeline stage transitions."""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.tables import RDProject, RDSubTask


class NotificationChain:
    """Sends structured notifications when pipeline stages complete."""

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
        """Called when a stage is marked as completed."""
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

        is_last = stage_index >= len(stages) - 1

        if is_last:
            await self._notify_manager(
                f"项目「{project.name}」已全部完成！最后阶段「{stage_name}」已结束。"
            )
            return

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
