import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.tables import PipelineTemplate, RDProject, RDSubTask, TaskRoute, TaskInstance
from app.services.pipeline_service import PipelineService


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.dispatch = AsyncMock(return_value=None)
    engine.db = MagicMock()
    return engine


@pytest.fixture
def sample_project(db_session):
    stages = [
        {"name": "灵感收集", "deliverables": [{"name": "参考图", "count": 3}], "timeout_days": 3,
         "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
         "notify_target": {"type": "next_stage_assignee"}},
        {"name": "灵感创作", "deliverables": [{"name": "创作方案", "count": 1}], "timeout_days": 5,
         "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
         "notify_target": {"type": "next_stage_assignee"}},
    ]
    project = RDProject(name="Test", stages_snapshot=json.dumps(stages), status="draft")
    db_session.add(project)
    db_session.flush()

    for idx, stage in enumerate(stages):
        sub = RDSubTask(
            project_id=project.id,
            title=stage["name"],
            assignees=json.dumps(["user_a"]),
            group_id="g1",
            platform="dingtalk",
            deliverables=json.dumps(stage["deliverables"]),
            status="pending",
            sort_order=idx,
            stage_index=idx,
            stage_name=stage["name"],
        )
        db_session.add(sub)
    db_session.commit()
    return project


def test_start_project(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    result = svc.start_project(sample_project.id)

    assert result is not None
    assert result["status"] == "active"
    first_sub = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 0,
    ).first()
    assert first_sub.status == "dispatched"


def test_start_project_already_active(db_session, sample_project, mock_engine):
    sample_project.status = "active"
    db_session.commit()

    svc = PipelineService(db_session, mock_engine)
    result = svc.start_project(sample_project.id)
    assert result is None


def test_advance_stage(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    sub0 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 0,
    ).first()
    sub0.status = "completed"
    db_session.commit()

    result = svc.advance_stage(sample_project.id, 0)
    assert result is not None

    sub1 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 1,
    ).first()
    assert sub1.status == "dispatched"


def test_advance_last_stage_completes_project(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    for sub in db_session.query(RDSubTask).filter(RDSubTask.project_id == sample_project.id).all():
        sub.status = "completed"
    db_session.commit()

    result = svc.advance_stage(sample_project.id, 1)
    assert result["status"] == "completed"


def test_rework_stage(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    sub0 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == sample_project.id,
        RDSubTask.stage_index == 0,
    ).first()
    sub0.status = "completed"
    db_session.commit()

    result = svc.rework_stage(sample_project.id, 0, reason="质量不达标")
    assert result is not None

    db_session.refresh(sub0)
    assert sub0.status == "rework"


def test_rework_invalid_stage(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    result = svc.rework_stage(sample_project.id, 0, reason="not yet started")
    assert result is None


def test_get_current_stages(db_session, sample_project, mock_engine):
    svc = PipelineService(db_session, mock_engine)
    svc.start_project(sample_project.id)

    stages = svc.get_current_stages(sample_project.id)
    assert len(stages) == 1
    assert stages[0].stage_index == 0
