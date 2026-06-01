import pytest

AUTH = {"Authorization": "Bearer changeme"}


def test_list_tasks_empty(client, db_session):
    """Test listing tasks when no tasks exist."""
    resp = client.get("/api/tasks", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


def test_list_tasks_with_data(client, db_session):
    """Test listing tasks with sample data."""
    from app.models.tables import TaskInstance, TaskRoute

    # Create a route first
    route = TaskRoute(
        handler_name="H",
        feishu_table_id="t",
        platform="dingtalk",
        group_id="g",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    # Create a task instance
    db_session.add(
        TaskInstance(
            handler_name="H",
            route_id=route.id,
            feishu_record_id="r1",
            platform="dingtalk",
            group_id="g",
            status="pending",
            flow_state="{}"
        )
    )
    db_session.commit()

    resp = client.get("/api/tasks", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["feishu_record_id"] == "r1"
    assert data["items"][0]["status"] == "pending"


def test_list_tasks_with_status_filter(client, db_session):
    """Test filtering tasks by status."""
    from app.models.tables import TaskInstance, TaskRoute

    route = TaskRoute(
        handler_name="H",
        feishu_table_id="t",
        platform="dingtalk",
        group_id="g",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    db_session.add(
        TaskInstance(
            handler_name="H",
            route_id=route.id,
            feishu_record_id="r1",
            platform="dingtalk",
            group_id="g",
            status="pending",
            flow_state="{}"
        )
    )
    db_session.add(
        TaskInstance(
            handler_name="H",
            route_id=route.id,
            feishu_record_id="r2",
            platform="dingtalk",
            group_id="g",
            status="completed",
            flow_state="{}"
        )
    )
    db_session.commit()

    # Filter by status
    resp = client.get("/api/tasks?status=pending", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "pending"


def test_list_tasks_with_handler_filter(client, db_session):
    """Test filtering tasks by handler name."""
    from app.models.tables import TaskInstance, TaskRoute

    route = TaskRoute(
        handler_name="H",
        feishu_table_id="t",
        platform="dingtalk",
        group_id="g",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    db_session.add(
        TaskInstance(
            handler_name="H1",
            route_id=route.id,
            feishu_record_id="r1",
            platform="dingtalk",
            group_id="g",
            status="pending",
            flow_state="{}"
        )
    )
    db_session.add(
        TaskInstance(
            handler_name="H2",
            route_id=route.id,
            feishu_record_id="r2",
            platform="dingtalk",
            group_id="g",
            status="pending",
            flow_state="{}"
        )
    )
    db_session.commit()

    # Filter by handler
    resp = client.get("/api/tasks?handler=H1", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["handler_name"] == "H1"


def test_task_detail(client, db_session):
    """Test getting detailed task information including participants."""
    from app.models.tables import TaskInstance, TaskRoute, TaskParticipant

    route = TaskRoute(
        handler_name="H",
        feishu_table_id="t",
        platform="dingtalk",
        group_id="g",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)
    db_session.flush()

    inst = TaskInstance(
        handler_name="H",
        route_id=route.id,
        feishu_record_id="r1",
        platform="dingtalk",
        group_id="g",
        status="pending",
        flow_state="{}"
    )
    db_session.add(inst)
    db_session.flush()

    # Add participants
    db_session.add(
        TaskParticipant(
            task_id=inst.id,
            feishu_user_id="f1",
            platform_user_id="d1",
            role="participant",
            status="pending"
        )
    )
    db_session.commit()

    resp = client.get(f"/api/tasks/{inst.id}", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == inst.id
    assert data["feishu_record_id"] == "r1"
    assert len(data["participants"]) == 1
    assert data["participants"][0]["feishu_user_id"] == "f1"


def test_task_detail_not_found(client, db_session):
    """Test getting detail for non-existent task."""
    resp = client.get("/api/tasks/999", headers=AUTH)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_unauthorized_access(client, db_session):
    """Test that requests without auth token fail."""
    resp = client.get("/api/tasks")
    assert resp.status_code in (401, 422)

    resp = client.get("/api/tasks/1")
    assert resp.status_code in (401, 422)


def test_invalid_token(client, db_session):
    """Test that requests with invalid token fail."""
    invalid_auth = {"Authorization": "Bearer wrong-token"}
    resp = client.get("/api/tasks", headers=invalid_auth)
    assert resp.status_code == 401
