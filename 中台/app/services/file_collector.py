"""File collection service for routing private chat files to task participants"""
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.tables import TaskParticipant, FileRecord, TaskInstance


class FileCollector:
    def __init__(self, db: Session, registry, adapters):
        self.db = db
        self.registry = registry
        self.adapters = adapters

    async def route_message(self, platform: str, user_id: str, conversation_id: str, message: dict):
        """Route a private chat message to the correct task participant"""
        msg_type = message.get("msg_type", "")
        if msg_type not in ("file", "picture"):
            return

        file_name = message.get("file_name", message.get("content", "unnamed"))
        download_code = message.get("download_code", "")

        # Find active participants for this user
        participants = self.db.query(TaskParticipant).filter(
            TaskParticipant.platform_user_id == user_id,
            TaskParticipant.status.in_(["confirmed", "submitted"])
        ).all()

        if not participants:
            adapter = self.adapters.get(platform)
            if adapter:
                await adapter.send_private_message(
                    user_id, "当前没有待处理的任务"
                )
            return

        target = participants[0]

        # Record the file
        record = FileRecord(
            task_id=target.task_id,
            participant_id=target.id,
            file_url=download_code,
            file_name=file_name,
            file_type=self._guess_type(file_name),
            platform_msg_id=download_code,
        )
        self.db.add(record)

        # Check deliverable requirements
        instance = self.db.query(TaskInstance).filter(
            TaskInstance.id == target.task_id
        ).first()
        deliverables = []
        if instance:
            meta = json.loads(instance.flow_state) if instance.flow_state else {}
            deliverables = meta.get("deliverables", [])

        # Count files for this participant
        file_count = self.db.query(FileRecord).filter(
            FileRecord.task_id == target.task_id,
            FileRecord.participant_id == target.id,
        ).count()

        # Check if deliverable count met
        if deliverables:
            total_required = sum(d.get("count", 1) for d in deliverables)
            if file_count >= total_required:
                target.status = "submitted"
        else:
            target.status = "submitted"

        self.db.commit()

        # Reply with progress
        adapter = self.adapters.get(platform)
        if adapter:
            if deliverables:
                total_required = sum(d.get("count", 1) for d in deliverables)
                await adapter.send_private_message(
                    user_id,
                    f"已收到「{file_name}」({file_count}/{total_required})"
                    + ("" if file_count < total_required else " — 交付物已齐，感谢！")
                )
            else:
                await adapter.send_private_message(
                    user_id, f"已收到「{file_name}」，感谢！"
                )

    def _guess_type(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        type_map = {
            "jpg": "image", "jpeg": "image", "png": "image", "gif": "image", "webp": "image",
            "pdf": "document", "doc": "document", "docx": "document",
            "xls": "document", "xlsx": "document",
            "mp4": "video", "mov": "video", "avi": "video",
        }
        return type_map.get(ext, "document")
