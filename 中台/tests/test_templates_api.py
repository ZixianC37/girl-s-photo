import json
import pytest

AUTH = {"Authorization": "Bearer changeme"}

SAMPLE_STAGES = [
    {
        "name": "灵感收集",
        "description": "团队提交灵感和参考素材",
        "default_assignees": [],
        "deliverables": [{"name": "参考图", "count": 5}],
        "timeout_days": 3,
        "reminder_policy": {
            "first_delay_hours": 24,
            "interval_hours": 12,
            "escalation_delay_hours": 24,
            "max_retries": 3,
        },
        "notify_target": {
            "type": "next_stage_assignee",
            "also_notify_manager": False,
        },
    }
]


def test_list_templates_empty(client, db_session):
    resp = client.get("/api/templates", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_template(client, db_session):
    resp = client.post(
        "/api/templates",
        json={"name": "标准写真研发", "description": "标准8阶段", "stages": SAMPLE_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "标准写真研发"
    assert data["description"] == "标准8阶段"
    assert "id" in data
    # stages is stored/returned as JSON string
    stages = json.loads(data["stages"])
    assert len(stages) == 1
    assert stages[0]["name"] == "灵感收集"


def test_create_template_validates_stages_length(client, db_session):
    resp = client.post(
        "/api/templates",
        json={"name": "Bad", "stages": [{"name": f"S{i}"} for i in range(21)]},
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_get_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="T1", stages=json.dumps(SAMPLE_STAGES))
    db_session.add(t)
    db_session.commit()

    resp = client.get(f"/api/templates/{t.id}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["name"] == "T1"


def test_get_template_not_found(client, db_session):
    resp = client.get("/api/templates/999", headers=AUTH)
    assert resp.status_code == 404


def test_update_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="Old", stages="[]")
    db_session.add(t)
    db_session.commit()

    resp = client.put(
        f"/api/templates/{t.id}",
        json={"name": "New", "stages": SAMPLE_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    stages = json.loads(resp.json()["stages"])
    assert len(stages) == 1


def test_delete_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="ToDelete", stages="[]")
    db_session.add(t)
    db_session.commit()

    resp = client.delete(f"/api/templates/{t.id}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


def test_delete_template_with_active_project_fails(client, db_session):
    from app.models.tables import PipelineTemplate, RDProject

    t = PipelineTemplate(name="InUse", stages="[]")
    db_session.add(t)
    db_session.flush()
    p = RDProject(name="P1", template_id=t.id, status="active")
    db_session.add(p)
    db_session.commit()

    resp = client.delete(f"/api/templates/{t.id}", headers=AUTH)
    assert resp.status_code == 409


def test_clone_template(client, db_session):
    from app.models.tables import PipelineTemplate

    t = PipelineTemplate(name="Original", description="desc", stages=json.dumps(SAMPLE_STAGES))
    db_session.add(t)
    db_session.commit()

    resp = client.post(f"/api/templates/{t.id}/clone", headers=AUTH)
    assert resp.status_code == 201
    clone = resp.json()
    assert clone["name"] == "Original (副本)"
    assert clone["id"] != t.id


def test_unauthorized(client, db_session):
    resp = client.get("/api/templates")
    assert resp.status_code in (401, 422)
