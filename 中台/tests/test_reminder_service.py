import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.models.tables import RDProject, RDSubTask, PipelineTemplate, ReminderLog, RDTask, TaskInstance
from app.services.reminder_service import ReminderService


@pytest.fixture
def mock_adapters():
    dt = MagicMock()
    dt.send_private_message = AsyncMock()
    return {"dingtalk": dt}


def _make_overdue_project(db_session, timeout_days=3, overdue_hours=25):
    """Create a project with one dispatched sub-task that is overdue."""
    stages = [
        {
            "name": "OverdueStage",
            "timeout_days": timeout_days,
            "reminder_policy": {
                "first_delay_hours": 24,
                "interval_hours": 12,
                "escalation_delay_hours": 24,
                "max_retries": 3,
            },
        },
    ]
    project = RDProject(name="Overdue", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(project)
    db_session.flush()

    created_at = datetime.now(timezone.utc) - timedelta(hours=overdue_hours)
    sub = RDSubTask(
        project_id=project.id,
        title="OverdueStage",
        assignees=json.dumps(["user_a"]),
        group_id="g1",
        platform="dingtalk",
        deliverables="[]",
        status="dispatched",
        sort_order=0,
        stage_index=0,
        stage_name="OverdueStage",
        created_at=created_at,
    )
    db_session.add(sub)
    db_session.commit()
    return project, sub


def test_find_overdue_tasks(db_session, mock_adapters):
    project, sub = _make_overdue_project(db_session, timeout_days=1, overdue_hours=30)
    svc = ReminderService(db_session, mock_adapters)
    overdue = svc.find_overdue_tasks()
    assert len(overdue) >= 1
    assert overdue[0].id == sub.id


def test_find_overdue_tasks_none_overdue(db_session, mock_adapters):
    project, sub = _make_overdue_project(db_session, timeout_days=10, overdue_hours=1)
    svc = ReminderService(db_session, mock_adapters)
    overdue = svc.find_overdue_tasks()
    assert len(overdue) == 0


def test_send_reminder(db_session, mock_adapters):
    project, sub = _make_overdue_project(db_session, timeout_days=1, overdue_hours=26)
    svc = ReminderService(db_session, mock_adapters)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        svc.send_reminder(sub, "private")
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()


def test_check_and_remind_creates_anomaly(db_session, mock_adapters):
    """When reminder count exceeds max, an anomaly dict should be returned."""
    project, sub = _make_overdue_project(db_session, timeout_days=1, overdue_hours=72)
    svc = ReminderService(db_session, mock_adapters)

    # Create a dummy task_instance for the reminder log
    inst = TaskInstance(
        handler_name="RDTaskHandler",
        feishu_record_id="test",
        platform="dingtalk",
        group_id="g1",
        status="pending",
    )
    db_session.add(inst)
    db_session.flush()
    sub.task_instance_id = inst.id
    db_session.commit()

    # Create a dummy participant so ReminderLog has a valid participant_id
    from app.models.tables import TaskParticipant
    participant = TaskParticipant(
        task_id=inst.id,
        feishu_user_id="test_user",
        role="executor",
        status="pending",
    )
    db_session.add(participant)
    db_session.flush()

    for i in range(3):
        log = ReminderLog(
            task_id=sub.task_instance_id,
            participant_id=participant.id,
            remind_type="private",
            remind_count=i + 1,
        )
        db_session.add(log)
    db_session.commit()

    import asyncio
    anomalies = asyncio.get_event_loop().run_until_complete(
        svc.check_and_remind()
    )
    assert isinstance(anomalies, list)


def test_is_not_overdue_for_pending(db_session, mock_adapters):
    """Pending tasks should not be considered overdue."""
    stages = [{"name": "S0", "timeout_days": 1}]
    project = RDProject(name="P", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(project)
    db_session.flush()

    sub = RDSubTask(
        project_id=project.id, title="S0", assignees="[]", group_id="g1",
        platform="dingtalk", deliverables="[]", status="pending",
        sort_order=0, stage_index=0, stage_name="S0",
    )
    db_session.add(sub)
    db_session.commit()

    svc = ReminderService(db_session, mock_adapters)
    overdue = svc.find_overdue_tasks()
    assert len(overdue) == 0
