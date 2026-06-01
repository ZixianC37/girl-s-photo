import json
import pytest

AUTH = {"Authorization": "Bearer changeme"}

SAMPLE_STAGES = [
    {
        "name": "灵感收集",
        "description": "团队提交灵感和参考素材",
        "default_assignees": ["user1"],
        "deliverables": [{"name": "参考图", "count": 5}],
        "timeout_days": 3,
    },
    {
        "name": "样片拍摄",
        "description": "执行样片拍摄",
        "default_assignees": ["user2"],
        "deliverables": [{"name": "样片", "count": 10}],
        "timeout_days": 5,
    },
]


def _create_template(client):
    """Helper: create a template and return its JSON."""
    resp = client.post(
        "/api/templates",
        json={"name": "标准写真研发", "stages": SAMPLE_STAGES},
        headers=AUTH,
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_project_from_template(client, db_session):
    template = _create_template(client)
    resp = client.post(
        "/api/projects",
        json={"name": "春季写真项目", "template_id": template["id"]},
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "春季写真项目"
    assert data["status"] == "draft"
    assert data["template_id"] == template["id"]
    assert json.loads(data["stages_snapshot"]) == json.loads(template["stages"])


def test_create_project_returns_sub_tasks(client, db_session):
    template = _create_template(client)
    resp = client.post(
        "/api/projects",
        json={"name": "项目A", "template_id": template["id"]},
        headers=AUTH,
    )
    data = resp.json()
    subs = data["sub_tasks"]
    assert len(subs) == 2
    assert subs[0]["stage_index"] == 0
    assert subs[0]["stage_name"] == "灵感收集"
    assert subs[0]["status"] == "pending"
    assert subs[1]["stage_index"] == 1
    assert subs[1]["stage_name"] == "样片拍摄"


def test_create_project_with_stage_overrides(client, db_session):
    template = _create_template(client)
    resp = client.post(
        "/api/projects",
        json={
            "name": "项目B",
            "template_id": template["id"],
            "stage_overrides": {
                "0": {"assignees": ["override_user"], "deadline": "2026-06-15T00:00:00Z"},
            },
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    data = resp.json()
    sub0 = data["sub_tasks"][0]
    assert json.loads(sub0["assignees"]) == ["override_user"]
    assert sub0["deadline"] is not None


def test_create_project_with_description(client, db_session):
    template = _create_template(client)
    resp = client.post(
        "/api/projects",
        json={
            "name": "项目C",
            "description": "测试描述",
            "template_id": template["id"],
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "测试描述"


def test_create_project_nonexistent_template(client, db_session):
    resp = client.post(
        "/api/projects",
        json={"name": "Ghost", "template_id": 9999},
        headers=AUTH,
    )
    assert resp.status_code == 404


def test_list_projects(client, db_session):
    template = _create_template(client)
    client.post(
        "/api/projects",
        json={"name": "P1", "template_id": template["id"]},
        headers=AUTH,
    )
    client.post(
        "/api/projects",
        json={"name": "P2", "template_id": template["id"]},
        headers=AUTH,
    )
    resp = client.get("/api/projects", headers=AUTH)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    names = {p["name"] for p in items}
    assert names == {"P1", "P2"}


def test_list_projects_filter_by_status(client, db_session):
    template = _create_template(client)
    client.post(
        "/api/projects",
        json={"name": "Draft1", "template_id": template["id"]},
        headers=AUTH,
    )
    # Create and activate another
    r = client.post(
        "/api/projects",
        json={"name": "Active1", "template_id": template["id"]},
        headers=AUTH,
    )
    pid = r.json()["id"]
    client.patch(f"/api/projects/{pid}", json={"status": "active"}, headers=AUTH)

    resp = client.get("/api/projects?status=active", headers=AUTH)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["name"] == "Active1"


def test_get_project_detail(client, db_session):
    template = _create_template(client)
    r = client.post(
        "/api/projects",
        json={"name": "Detail项目", "template_id": template["id"]},
        headers=AUTH,
    )
    pid = r.json()["id"]

    resp = client.get(f"/api/projects/{pid}", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail项目"
    assert len(data["sub_tasks"]) == 2


def test_get_project_not_found(client, db_session):
    resp = client.get("/api/projects/999", headers=AUTH)
    assert resp.status_code == 404


def test_patch_project_status(client, db_session):
    template = _create_template(client)
    r = client.post(
        "/api/projects",
        json={"name": "Status项目", "template_id": template["id"]},
        headers=AUTH,
    )
    pid = r.json()["id"]

    resp = client.patch(
        f"/api/projects/{pid}",
        json={"status": "active"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # Can also pause
    resp = client.patch(
        f"/api/projects/{pid}",
        json={"status": "paused"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_advance_project(client, db_session):
    template = _create_template(client)
    r = client.post(
        "/api/projects",
        json={"name": "Advance项目", "template_id": template["id"]},
        headers=AUTH,
    )
    pid = r.json()["id"]

    # Start the project first (moves from draft -> active)
    start_resp = client.post(f"/api/projects/{pid}/start", headers=AUTH)
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "active"

    resp = client.post(
        f"/api/projects/{pid}/advance",
        json={"stage_index": 0},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Stage 0 should be completed now
    stage0 = [s for s in data["sub_tasks"] if s["stage_index"] == 0][0]
    assert stage0["status"] == "completed"


def test_rework_stage(client, db_session):
    template = _create_template(client)
    r = client.post(
        "/api/projects",
        json={"name": "Rework项目", "template_id": template["id"]},
        headers=AUTH,
    )
    pid = r.json()["id"]

    # Start and advance stage 0 so stage 1 becomes dispatched
    client.post(f"/api/projects/{pid}/start", headers=AUTH)
    client.post(f"/api/projects/{pid}/advance", json={"stage_index": 0}, headers=AUTH)

    # Now rework stage 1 (which should be dispatched after advancing past stage 0)
    resp = client.post(
        f"/api/projects/{pid}/rework",
        json={"stage_index": 1, "reason": "质量问题"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    stage1 = [s for s in data["sub_tasks"] if s["stage_index"] == 1][0]
    assert stage1["status"] == "rework"


def test_delete_project_cascades_sub_tasks(client, db_session):
    from app.models.tables import RDSubTask

    template = _create_template(client)
    r = client.post(
        "/api/projects",
        json={"name": "ToDelete", "template_id": template["id"]},
        headers=AUTH,
    )
    pid = r.json()["id"]

    # Verify sub_tasks exist
    assert db_session.query(RDSubTask).filter(RDSubTask.project_id == pid).count() == 2

    resp = client.delete(f"/api/projects/{pid}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Verify cascade delete
    assert db_session.query(RDSubTask).filter(RDSubTask.project_id == pid).count() == 0


def test_delete_project_not_found(client, db_session):
    resp = client.delete("/api/projects/999", headers=AUTH)
    assert resp.status_code == 404


def test_unauthorized(client, db_session):
    resp = client.get("/api/projects")
    assert resp.status_code in (401, 422)
