import pytest

AUTH = {"Authorization": "Bearer changeme"}


def test_list_rd_tasks_empty(client, db_session):
    """Test listing RD tasks when no tasks exist."""
    resp = client.get("/api/rd-tasks", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_rd_task(client, db_session):
    """Test creating an RD task with sub-tasks."""
    resp = client.post(
        "/api/rd-tasks",
        json={
            "title": "春季新品研发",
            "description": "2026春季新品",
            "sub_tasks": [
                {
                    "title": "样片拍摄",
                    "description": "拍摄样片",
                    "assignees": ["f1"],
                    "group_id": "g1",
                    "platform": "dingtalk",
                    "sort_order": 1,
                    "deliverables": [
                        {"name": "样片A", "type": "image", "count": 5}
                    ]
                }
            ]
        },
        headers=AUTH
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "春季新品研发"
    assert data["description"] == "2026春季新品"
    assert data["status"] == "active"
    assert len(data["sub_tasks"]) == 1
    assert data["sub_tasks"][0]["title"] == "样片拍摄"
    assert data["sub_tasks"][0]["assignees"] == ["f1"]
    assert data["sub_tasks"][0]["platform"] == "dingtalk"
    assert data["sub_tasks"][0]["group_id"] == "g1"
    assert data["sub_tasks"][0]["sort_order"] == 1
    assert len(data["sub_tasks"][0]["deliverables"]) == 1
    assert data["sub_tasks"][0]["deliverables"][0]["name"] == "样片A"
    assert data["sub_tasks"][0]["status"] in ["dispatched", "pending"]  # May fail dispatch


def test_create_rd_task_multiple_subtasks(client, db_session):
    """Test creating an RD task with multiple sub-tasks."""
    resp = client.post(
        "/api/rd-tasks",
        json={
            "title": "夏季新品研发",
            "description": "2026夏季新品",
            "sub_tasks": [
                {
                    "title": "概念设计",
                    "assignees": ["f1", "f2"],
                    "group_id": "g1",
                    "platform": "dingtalk",
                    "sort_order": 1
                },
                {
                    "title": "样片拍摄",
                    "assignees": ["f3"],
                    "group_id": "g2",
                    "platform": "wecom",
                    "sort_order": 2,
                    "deadline": "2026-06-30T23:59:59Z"
                }
            ]
        },
        headers=AUTH
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "夏季新品研发"
    assert len(data["sub_tasks"]) == 2
    assert data["sub_tasks"][0]["title"] == "概念设计"
    assert len(data["sub_tasks"][0]["assignees"]) == 2
    assert data["sub_tasks"][1]["title"] == "样片拍摄"
    assert data["sub_tasks"][1]["deadline"] is not None


def test_list_rd_tasks_with_data(client, db_session):
    """Test listing RD tasks with sample data."""
    from app.models.tables import RDTask, RDSubTask
    import json

    # Create an RD task directly
    rd = RDTask(title="测试任务", description="测试描述", status="active")
    db_session.add(rd)
    db_session.flush()

    sub = RDSubTask(
        rd_task_id=rd.id,
        title="子任务1",
        description="子任务描述",
        assignees=json.dumps(["f1"]),
        group_id="g1",
        platform="dingtalk",
        sort_order=0
    )
    db_session.add(sub)
    db_session.commit()

    resp = client.get("/api/rd-tasks", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "测试任务"
    assert data[0]["sub_task_count"] == 1
    assert data[0]["status"] == "active"


def test_get_rd_task_detail(client, db_session):
    """Test getting detailed RD task information."""
    from app.models.tables import RDTask, RDSubTask, TaskInstance, TaskParticipant
    import json

    # Create an RD task
    rd = RDTask(title="详细任务", description="详细描述", status="active")
    db_session.add(rd)
    db_session.flush()

    sub = RDSubTask(
        rd_task_id=rd.id,
        title="子任务1",
        assignees=json.dumps(["f1"]),
        group_id="g1",
        platform="dingtalk",
        sort_order=0,
        status="dispatched"
    )
    db_session.add(sub)
    db_session.flush()

    # Create a task instance
    inst = TaskInstance(
        handler_name="RDTaskHandler",
        feishu_record_id=f"rd_sub_task_{sub.id}",
        platform="dingtalk",
        group_id="g1",
        status="pending"
    )
    db_session.add(inst)
    db_session.flush()

    sub.task_instance_id = inst.id

    # Add participants
    db_session.add(
        TaskParticipant(
            task_id=inst.id,
            feishu_user_id="f1",
            role="participant",
            status="completed"
        )
    )
    db_session.add(
        TaskParticipant(
            task_id=inst.id,
            feishu_user_id="f2",
            role="participant",
            status="pending"
        )
    )
    db_session.commit()

    resp = client.get(f"/api/rd-tasks/{rd.id}", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == rd.id
    assert data["title"] == "详细任务"
    assert len(data["sub_tasks"]) == 1
    assert data["sub_tasks"][0]["title"] == "子任务1"
    assert data["sub_tasks"][0]["progress"] == "1/2"


def test_get_rd_task_not_found(client, db_session):
    """Test getting detail for non-existent RD task."""
    resp = client.get("/api/rd-tasks/999", headers=AUTH)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_delete_rd_task(client, db_session):
    """Test deleting an RD task."""
    from app.models.tables import RDTask, RDSubTask

    # Create an RD task
    created = client.post(
        "/api/rd-tasks",
        json={
            "title": "测试任务",
            "sub_tasks": [
                {
                    "title": "子任务1",
                    "assignees": ["f1"],
                    "group_id": "g1",
                    "platform": "dingtalk",
                    "sort_order": 0
                }
            ]
        },
        headers=AUTH
    )
    assert created.status_code == 201
    tid = created.json()["id"]

    # Delete it
    resp = client.delete(f"/api/rd-tasks/{tid}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Verify it's gone
    resp = client.get("/api/rd-tasks", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_rd_task_with_cascade(client, db_session):
    """Test that deleting an RD task cascades to task instances."""
    from app.models.tables import RDTask, RDSubTask, TaskInstance, TaskRoute, TaskParticipant, FileRecord
    import json

    # Create an RD task directly
    rd = RDTask(title="级联测试", description="级联测试", status="active")
    db_session.add(rd)
    db_session.flush()

    sub = RDSubTask(
        rd_task_id=rd.id,
        title="子任务1",
        assignees=json.dumps(["f1"]),
        group_id="g1",
        platform="dingtalk",
        sort_order=0
    )
    db_session.add(sub)
    db_session.flush()

    # Create task route
    route = TaskRoute(
        handler_name="RDTaskHandler",
        feishu_table_id=f"rd_sub_task:{sub.id}",
        platform="dingtalk",
        group_id="g1",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    sub.task_route_id = route.id

    # Create task instance
    inst = TaskInstance(
        handler_name="RDTaskHandler",
        route_id=route.id,
        feishu_record_id=f"rd_sub_task_{sub.id}",
        platform="dingtalk",
        group_id="g1",
        status="pending"
    )
    db_session.add(inst)
    db_session.flush()

    sub.task_instance_id = inst.id

    # Add participants
    db_session.add(
        TaskParticipant(
            task_id=inst.id,
            feishu_user_id="f1",
            role="participant",
            status="pending"
        )
    )

    # Add file record
    db_session.add(
        FileRecord(
            task_id=inst.id,
            participant_id=1,
            file_url="http://example.com/file.jpg",
            file_name="file.jpg",
            file_type="image"
        )
    )
    db_session.commit()

    # Delete the RD task
    inst_id = inst.id  # Store ID before deletion
    route_id = route.id  # Store ID before deletion
    resp = client.delete(f"/api/rd-tasks/{rd.id}", headers=AUTH)
    assert resp.status_code == 200

    # Verify cascade deletion
    assert db_session.query(RDTask).filter(RDTask.id == rd.id).first() is None
    assert db_session.query(RDSubTask).filter(RDSubTask.id == sub.id).first() is None
    assert db_session.query(TaskInstance).filter(TaskInstance.id == inst_id).first() is None
    assert db_session.query(TaskRoute).filter(TaskRoute.id == route_id).first() is None


def test_unauthorized_access(client, db_session):
    """Test that requests without auth token fail."""
    resp = client.get("/api/rd-tasks")
    assert resp.status_code in (401, 422)

    resp = client.post("/api/rd-tasks", json={"title": "Test"})
    assert resp.status_code in (401, 422)

    resp = client.get("/api/rd-tasks/1")
    assert resp.status_code in (401, 422)

    resp = client.delete("/api/rd-tasks/1")
    assert resp.status_code in (401, 422)


def test_invalid_token(client, db_session):
    """Test that requests with invalid token fail."""
    invalid_auth = {"Authorization": "Bearer wrong-token"}
    resp = client.get("/api/rd-tasks", headers=invalid_auth)
    assert resp.status_code == 401

    resp = client.post("/api/rd-tasks", json={"title": "Test"}, headers=invalid_auth)
    assert resp.status_code == 401
