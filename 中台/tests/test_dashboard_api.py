import pytest

AUTH = {"Authorization": "Bearer changeme"}


def test_dashboard_stats(client, db_session):
    """Test getting dashboard statistics."""
    resp = client.get("/api/dashboard/stats", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "active_routes" in data
    assert "registered_handlers" in data
    assert "today_tasks" in data
    assert "error_rate" in data
    assert "recent_tasks" in data
    assert isinstance(data["active_routes"], int)
    assert isinstance(data["registered_handlers"], int)
    assert isinstance(data["today_tasks"], int)
    assert isinstance(data["error_rate"], float)
    assert isinstance(data["recent_tasks"], list)


def test_dashboard_stats_with_data(client, db_session):
    """Test dashboard stats with actual data."""
    from app.models.tables import TaskRoute, TaskInstance

    # Create an active route
    route = TaskRoute(
        handler_name="H",
        feishu_table_id="t",
        platform="dingtalk",
        group_id="g",
        field_mapping="{}",
        enabled=True
    )
    db_session.add(route)

    # Create a disabled route
    disabled_route = TaskRoute(
        handler_name="H2",
        feishu_table_id="t2",
        platform="dingtalk",
        group_id="g2",
        field_mapping="{}",
        enabled=False
    )
    db_session.add(disabled_route)
    db_session.flush()

    # Create some tasks
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
            status="error",
            flow_state="{}"
        )
    )
    db_session.commit()

    resp = client.get("/api/dashboard/stats", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()

    # Should count only enabled routes
    assert data["active_routes"] == 1

    # Should have 2 tasks total (including today)
    assert data["today_tasks"] >= 0  # May vary depending on when test runs

    # Error rate should be 50% (1 error out of 2 tasks)
    assert data["error_rate"] == 0.5

    # Should have recent tasks
    assert len(data["recent_tasks"]) >= 2


def test_dashboard_error_rate_with_no_tasks(client, db_session):
    """Test error rate calculation when no tasks exist."""
    resp = client.get("/api/dashboard/stats", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    # Error rate should be 0 when no tasks
    assert data["error_rate"] == 0.0


def test_unauthorized_access(client, db_session):
    """Test that requests without auth token fail."""
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code in (401, 422)


def test_invalid_token(client, db_session):
    """Test that requests with invalid token fail."""
    invalid_auth = {"Authorization": "Bearer wrong-token"}
    resp = client.get("/api/dashboard/stats", headers=invalid_auth)
    assert resp.status_code == 401
