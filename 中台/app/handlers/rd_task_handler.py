import json
from app.engine.handler_base import BaseHandler
from app.models.types import TaskData, CardData, CardSection, CardAction, FlowDefinition, RoleDefinition, ReminderRule, TaskUpdate


class RDTaskHandler(BaseHandler):

    def parse_event(self, event, field_mapping):
        if isinstance(field_mapping, str):
            field_mapping = json.loads(field_mapping)
        return TaskData(
            title=field_mapping.get("title", "研发子任务"),
            participants=field_mapping.get("assignees", []),
            deadline=None,
            parameters={
                "rd_sub_task_id": field_mapping.get("rd_sub_task_id"),
                "title": field_mapping.get("title", "研发子任务"),
                "assignees": field_mapping.get("assignees", []),
                "deliverables": field_mapping.get("deliverables", []),
            },
        )

    def get_flow(self):
        return FlowDefinition(
            states=["pending", "confirmed", "submitted", "completed"],
            initial="pending",
        )

    def get_roles(self):
        return RoleDefinition(roles=["creator", "assignee"], default_role="assignee")

    def build_card(self, task, state):
        # Read sub-task metadata from flow_state (stored by TaskEngine.dispatch)
        meta = {}
        if isinstance(task.flow_state, str):
            try:
                meta = json.loads(task.flow_state)
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(task.flow_state, dict):
            meta = task.flow_state

        title = meta.get("title", "研发子任务")
        deliverables = meta.get("deliverables", [])
        assignees = meta.get("assignees", [])

        sections = []

        # Deadline
        if task.deadline:
            sections.append(CardSection(text=f"截止时间：{task.deadline.strftime('%Y-%m-%d')}"))

        # Deliverables
        if deliverables:
            items = [f"{d.get('name', '?')} × {d.get('count', 1)}" for d in deliverables]
            sections.append(CardSection(text=f"交付物：{', '.join(items)}"))

        # Assignees
        if assignees:
            sections.append(CardSection(text=f"负责人：{', '.join(assignees)}"))

        # Participant progress
        progress = meta.get("participant_progress")
        if progress and state in ("confirmed", "submitted"):
            sections.append(CardSection(
                text=f"已确认：{progress['confirmed']}/{progress['total']} 人"
            ))

        # Status indicator for non-pending states
        status_text = {
            "confirmed": "已确认",
            "submitted": "已提交",
            "completed": "已完成",
            "rework": "返工中",
        }
        if state in status_text:
            sections.insert(0, CardSection(text=status_text[state]))

        # Actions by state
        actions = []
        if state == "pending":
            actions.append(CardAction(label="确认接单", action="confirm", style="primary"))
            actions.append(CardAction(label="上报问题", action="report_problem", style="danger"))
        elif state == "confirmed":
            actions.append(CardAction(label="上传文件", action="upload"))

        return CardData(
            title=f"子任务：{title}",
            sections=sections,
            actions=actions,
        )

    def get_reminder_rules(self):
        return [
            ReminderRule(trigger="time_elapsed", target="private", message_template="您有未完成的研发子任务"),
        ]

    def handle_callback(self, action, user, task):
        from datetime import datetime, timezone

        status_map = {
            "confirm": "confirmed",
            "upload": "submitted",
            "rework": "submitted",
            "report_problem": "submitted",
        }
        new_status = status_map.get(action)

        flow_update = None
        if new_status:
            flow_update = {
                f"{new_status}_by": user,
                f"{new_status}_at": datetime.now(timezone.utc).isoformat(),
            }

        if action == "rework":
            flow_update["rework_by"] = user
            flow_update["rework_at"] = datetime.now(timezone.utc).isoformat()
        elif action == "report_problem":
            flow_update["reported_problem_by"] = user
            flow_update["reported_problem_at"] = datetime.now(timezone.utc).isoformat()

        return TaskUpdate(status=new_status, flow_state_update=flow_update)
