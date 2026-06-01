"""End-to-end integration test for the full pipeline flow."""
import json
import pytest
from app.models.tables import PipelineTemplate, RDProject, RDSubTask

AUTH = {"Authorization": "Bearer changeme"}

THREE_STAGES = [
    {"name": "灵感收集", "description": "collect", "default_assignees": ["u1"],
     "deliverables": [{"name": "参考图", "count": 3}], "timeout_days": 3,
     "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
     "notify_target": {"type": "next_stage_assignee"}},
    {"name": "灵感创作", "description": "create", "default_assignees": ["u2"],
     "deliverables": [{"name": "方案", "count": 1}], "timeout_days": 5,
     "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
     "notify_target": {"type": "next_stage_assignee"}},
    {"name": "品鉴会", "description": "review", "default_assignees": ["u3"],
     "deliverables": [{"name": "品鉴结论", "count": 1}], "timeout_days": 2,
     "reminder_policy": {"first_delay_hours": 24, "interval_hours": 12, "max_retries": 3},
     "notify_target": {"type": "manager", "also_notify_manager": True}},
]


def _create_template(client):
    resp = client.post(
        "/api/templates",
        json={"name": "3阶段模板", "stages": THREE_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 201
    return resp.json()


def test_full_pipeline_flow(client, db_session):
    """create template -> create project -> start -> complete stages -> project done"""

    # 1. Create template
    template = _create_template(client)
    template_id = template["id"]

    # 2. Create project from template
    resp = client.post("/api/projects", json={
        "name": "集成测试项目",
        "template_id": template_id,
    }, headers=AUTH)
    assert resp.status_code == 201
    project = resp.json()
    project_id = project["id"]
    assert project["status"] == "draft"
    assert len(project["sub_tasks"]) == 3

    # 3. Start project
    resp = client.post(f"/api/projects/{project_id}/start", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 4. Verify first stage is dispatched
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    subs = resp.json()["sub_tasks"]
    assert subs[0]["status"] == "dispatched"
    assert subs[1]["status"] == "pending"
    assert subs[2]["status"] == "pending"

    # 5. Complete stage 0 and advance
    resp = client.post(f"/api/projects/{project_id}/advance",
                       json={"stage_index": 0}, headers=AUTH)
    assert resp.status_code == 200

    # 6. Verify stage 1 is now dispatched
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    subs = resp.json()["sub_tasks"]
    assert subs[0]["status"] == "completed"
    assert subs[1]["status"] == "dispatched"
    assert subs[2]["status"] == "pending"

    # 7. Complete stage 1 and advance
    resp = client.post(f"/api/projects/{project_id}/advance",
                       json={"stage_index": 1}, headers=AUTH)
    assert resp.status_code == 200

    # 8. Verify stage 2 dispatched
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    subs = resp.json()["sub_tasks"]
    assert subs[1]["status"] == "completed"
    assert subs[2]["status"] == "dispatched"

    # 9. Complete stage 2 and advance - should complete project
    resp = client.post(f"/api/projects/{project_id}/advance",
                       json={"stage_index": 2}, headers=AUTH)
    assert resp.status_code == 200

    # 10. Project should be completed
    resp = client.get(f"/api/projects/{project_id}", headers=AUTH)
    assert resp.json()["status"] == "completed"


def test_rework_flow(client, db_session):
    """complete stage -> rework -> resolve anomaly -> continue"""

    # Create and start project
    resp = client.post("/api/templates",
                       json={"name": "Rework模板", "stages": THREE_STAGES[:2]}, headers=AUTH)
    template_id = resp.json()["id"]

    resp = client.post("/api/projects", json={
        "name": "Rework项目", "template_id": template_id,
    }, headers=AUTH)
    project_id = resp.json()["id"]

    client.post(f"/api/projects/{project_id}/start", headers=AUTH)

    # Complete stage 0
    client.post(f"/api/projects/{project_id}/advance",
                json={"stage_index": 0}, headers=AUTH)

    # Now stage 1 is dispatched - rework it
    resp = client.post(f"/api/projects/{project_id}/rework",
                       json={"stage_index": 1, "reason": "质量不达标"}, headers=AUTH)
    assert resp.status_code == 200

    # Verify stage 1 is in rework
    s1 = db_session.query(RDSubTask).filter(
        RDSubTask.project_id == project_id, RDSubTask.stage_index == 1
    ).first()
    assert s1.status == "rework"

    # Check anomaly exists
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    anomalies = resp.json()
    assert any(a["type"] == "rework" for a in anomalies)

    # Resume via anomaly
    resp = client.patch(f"/api/anomalies/{s1.id}", json={"action": "dismiss"}, headers=AUTH)
    assert resp.status_code == 200

    db_session.refresh(s1)
    assert s1.status == "dispatched"


def test_project_pause_resume(client, db_session):
    """Test pausing and resuming a project."""
    resp = client.post("/api/templates",
                       json={"name": "Pause模板", "stages": THREE_STAGES[:2]}, headers=AUTH)
    template_id = resp.json()["id"]

    resp = client.post("/api/projects", json={
        "name": "Pause项目", "template_id": template_id,
    }, headers=AUTH)
    project_id = resp.json()["id"]

    # Start then pause
    client.post(f"/api/projects/{project_id}/start", headers=AUTH)
    resp = client.patch(f"/api/projects/{project_id}", json={"status": "paused"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"

    # Resume
    resp = client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
