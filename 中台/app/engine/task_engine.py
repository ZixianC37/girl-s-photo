"""Task engine for dispatching events and handling callbacks"""
import json
from typing import Optional, Dict, Any
from app.models.tables import TaskInstance, TaskRoute, TaskParticipant
from app.models.types import TaskData


class TaskEngine:
    """
    Core task engine that dispatches events to handlers
    and manages task lifecycle through callbacks.
    """

    def __init__(self, db, registry, adapters):
        """
        Initialize the task engine

        Args:
            db: Database session
            registry: HandlerRegistry instance
            adapters: Dict of platform adapters (e.g., {"dingtalk": adapter})
        """
        self.db = db
        self.registry = registry
        self.adapters = adapters

    async def dispatch(self, table_id: str, record_id: str, action: str, fields: Dict[str, Any]) -> Optional[TaskInstance]:
        """
        Core dispatch: route → handler → adapter

        Args:
            table_id: Feishu table ID
            record_id: Feishu record ID
            action: Event action (e.g., "create", "update")
            fields: Raw event fields

        Returns:
            TaskInstance if successful, None if no route found
        """
        # 1. Query task_route WHERE feishu_table_id = table_id AND enabled
        route = self.db.query(TaskRoute).filter(
            TaskRoute.feishu_table_id == table_id,
            TaskRoute.enabled == True
        ).first()
        if not route:
            return None

        # 2. Get handler from registry
        handler_cls = self.registry.get(route.handler_name)
        if not handler_cls:
            return None
        handler = handler_cls()

        # 3. handler.parse_event(event, route.field_mapping)
        field_mapping = json.loads(route.field_mapping) if isinstance(route.field_mapping, str) else route.field_mapping
        event = {"table_id": table_id, "record_id": record_id, "action": action, "fields": fields}
        task_data = handler.parse_event(event, field_mapping)

        if not task_data:
            return None

        # 4. Get flow and initial state
        flow = handler.get_flow()

        # 5. Create task_instance row
        instance = TaskInstance(
            handler_name=route.handler_name,
            route_id=route.id,
            feishu_record_id=record_id,
            platform=route.platform,
            group_id=route.group_id,
            status=flow.initial,
            flow_state=json.dumps(task_data.parameters or {}),
            deadline=task_data.deadline
        )
        self.db.add(instance)
        self.db.flush()

        # 6. handler.build_card(task, initial_state)
        card = handler.build_card(instance, flow.initial)

        # 7. adapter.send_group_card(route.group_id, card)
        adapter = self.adapters.get(route.platform)
        card_id = None
        if adapter:
            card_id = await adapter.send_group_card(route.group_id, card)

        # 8. Update task_instance.card_id
        instance.card_id = card_id

        # 9. Create task_participant rows
        for participant_id in task_data.participants:
            participant = TaskParticipant(
                task_id=instance.id,
                feishu_user_id=participant_id,
                platform_user_id=None,  # Will be resolved by identity mapping
                role="participant",
                status="pending"
            )
            self.db.add(participant)

        self.db.commit()
        return instance

    async def handle_callback(self, platform: str, card_id: str, user_id: str, action: str) -> Optional[TaskInstance]:
        """
        Handle user interaction from DingTalk/WeCom

        Args:
            platform: Platform name (e.g., "dingtalk", "wecom")
            card_id: Interactive card ID
            user_id: Platform user ID
            action: Action performed by user

        Returns:
            Updated TaskInstance if found, None otherwise
        """
        # 1. Query task_instance by card_id
        instance = self.db.query(TaskInstance).filter(
            TaskInstance.card_id == card_id
        ).first()
        if not instance:
            return None

        # 2. Get handler
        handler_cls = self.registry.get(instance.handler_name)
        if not handler_cls:
            return None
        handler = handler_cls()

        # 3. handler.handle_callback(action, user, task)
        # Resolve participant: try platform_user_id first, then feishu_user_id fallback
        participant = self.db.query(TaskParticipant).filter(
            TaskParticipant.task_id == instance.id,
            TaskParticipant.platform_user_id == user_id
        ).first()

        if not participant:
            from app.services.identity import IdentityService
            identity = IdentityService(self.db)
            feishu_uid = identity.get_feishu_user_id(user_id, platform)
            if feishu_uid:
                participant = self.db.query(TaskParticipant).filter(
                    TaskParticipant.task_id == instance.id,
                    TaskParticipant.feishu_user_id == feishu_uid
                ).first()

        update = handler.handle_callback(action, user_id, instance)

        # 4. Update participant status
        if participant and update.status:
            participant.status = update.status

        # 5. Merge flow_state_update
        if update.flow_state_update:
            current_state = json.loads(instance.flow_state) if instance.flow_state else {}
            current_state.update(update.flow_state_update)
            instance.flow_state = json.dumps(current_state)

        if update.status:
            instance.status = update.status

        # 5b. Check if all participants are done
        if participant and update.status:
            all_participants = self.db.query(TaskParticipant).filter(
                TaskParticipant.task_id == instance.id
            ).all()
            all_done = all(
                p.status in ("submitted", "completed")
                for p in all_participants
            )
            if all_done and len(all_participants) > 0:
                instance.status = "completed"
                self._on_task_instance_completed(instance)

            # Update participant progress in flow_state
            current_state = json.loads(instance.flow_state) if instance.flow_state else {}
            progress = {
                "total": len(all_participants),
                "confirmed": sum(1 for p in all_participants if p.status in ("confirmed", "submitted", "completed")),
                "submitted": sum(1 for p in all_participants if p.status in ("submitted", "completed")),
            }
            current_state["participant_progress"] = progress
            instance.flow_state = json.dumps(current_state)

        # 6. handler.build_card for updated state
        card = handler.build_card(instance, instance.status)

        # 7. adapter.update_group_card
        adapter = self.adapters.get(platform)
        if adapter:
            await adapter.update_group_card(card_id, card)

        self.db.commit()
        return instance

    def _on_task_instance_completed(self, instance: TaskInstance) -> None:
        """Hook called when a task instance reaches 'completed' status.

        Updates the parent RDSubTask status to 'completed' if it belongs to a project.
        """
        from app.models.tables import RDSubTask

        sub_task = self.db.query(RDSubTask).filter(
            RDSubTask.task_instance_id == instance.id,
            RDSubTask.project_id.isnot(None),
        ).first()

        if sub_task:
            sub_task.status = "completed"

    async def handle_private_message(self, platform: str, user_id: str, conversation_id: str, message: dict):
        """Handle private chat message (file upload, text) from DingTalk/WeCom"""
        msg_type = message.get("msg_type", "")
        if msg_type not in ("file", "picture"):
            return

        from app.services.file_collector import FileCollector
        collector = FileCollector(self.db, self.registry, self.adapters)
        await collector.route_message(platform, user_id, conversation_id, message)
