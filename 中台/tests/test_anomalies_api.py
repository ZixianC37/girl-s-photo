import json
import pytest
from app.models.tables import RDProject, RDSubTask, PipelineTemplate

AUTH = {"Authorization": "Bearer changeme"}


def _make_project_with_anomaly(db_session, status="rework"):
    stages = [{"name": "AnomStage", "timeout_days": 1}]
    p = RDProject(name="AnomalyProject", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(p)
    db_session.flush()

    sub = RDSubTask(
        project_id=p.id, title="AnomStage",
        assignees=json.dumps(["user_a"]),
        group_id="g1", platform="dingtalk", deliverables="[]",
        status=status, sort_order=0, stage_index=0, stage_name="AnomStage",
    )
    db_session.add(sub)
    db_session.commit()
    return p, sub


def test_list_anomalies_empty(client, db_session):
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_anomalies_finds_rework(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["type"] == "rework"


def test_list_anomalies_finds_blocked(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="blocked")
    resp = client.get("/api/anomalies", headers=AUTH)
    assert resp.status_code == 200
    assert any(a["type"] == "blocked" for a in resp.json())


def test_list_anomalies_filter_by_project(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    resp = client.get(f"/api/anomalies?project_id={p.id}", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/api/anomalies?project_id=999", headers=AUTH)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_resolve_anomaly_resume(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="blocked")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "resume"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert sub.status == "dispatched"


def test_resolve_anomaly_skip(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="blocked")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "skip"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert sub.status == "completed"


def test_resolve_anomaly_reassign(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "reassign", "data": {"assignees": ["user_b"]}},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert "user_b" in json.loads(sub.assignees)


def test_resolve_anomaly_dismiss(client, db_session):
    p, sub = _make_project_with_anomaly(db_session, status="rework")
    anomaly_id = sub.id

    resp = client.patch(
        f"/api/anomalies/{anomaly_id}",
        json={"action": "dismiss"},
        headers=AUTH,
    )
    assert resp.status_code == 200
    db_session.refresh(sub)
    assert sub.status == "dispatched"


def test_resolve_anomaly_not_found(client, db_session):
    resp = client.patch(
        "/api/anomalies/999",
        json={"action": "resume"},
        headers=AUTH,
    )
    assert resp.status_code == 404
