import pytest

AUTH = {"Authorization": "Bearer changeme"}


def test_create_group(client, db_session):
    """Test creating a new group mapping."""
    resp = client.post(
        "/api/groups",
        json={"name": "品鉴会通知群", "group_id": "group_123", "platform": "dingtalk"},
        headers=AUTH
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "品鉴会通知群"
    assert data["group_id"] == "group_123"
    assert data["platform"] == "dingtalk"
    assert "id" in data


def test_create_duplicate_group(client, db_session):
    """Test that creating a duplicate group_id fails."""
    client.post(
        "/api/groups",
        json={"name": "群1", "group_id": "g1", "platform": "dingtalk"},
        headers=AUTH
    )

    resp = client.post(
        "/api/groups",
        json={"name": "群2", "group_id": "g1", "platform": "wecom"},
        headers=AUTH
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


def test_list_groups(client, db_session):
    """Test listing all groups."""
    client.post(
        "/api/groups",
        json={"name": "群1", "group_id": "g1", "platform": "dingtalk"},
        headers=AUTH
    )
    client.post(
        "/api/groups",
        json={"name": "群2", "group_id": "g2", "platform": "wecom"},
        headers=AUTH
    )

    resp = client.get("/api/groups", headers=AUTH)
    assert resp.status_code == 200
    groups = resp.json()
    assert len(groups) == 2

    # Verify group data
    group_ids = {g["group_id"] for g in groups}
    assert "g1" in group_ids
    assert "g2" in group_ids


def test_list_empty_groups(client, db_session):
    """Test listing groups when none exist."""
    resp = client.get("/api/groups", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_group(client, db_session):
    """Test deleting a group by ID."""
    resp = client.post(
        "/api/groups",
        json={"name": "群1", "group_id": "g1", "platform": "dingtalk"},
        headers=AUTH
    )
    gid = resp.json()["id"]

    resp = client.delete(f"/api/groups/{gid}", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Group deleted successfully"

    # Verify group is deleted
    resp = client.get("/api/groups", headers=AUTH)
    assert resp.json() == []


def test_delete_nonexistent_group(client, db_session):
    """Test deleting a group that doesn't exist."""
    resp = client.delete("/api/groups/999", headers=AUTH)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_unauthorized_access(client, db_session):
    """Test that requests without auth token fail."""
    resp = client.get("/api/groups")
    # FastAPI returns 422 for missing required header
    assert resp.status_code in (401, 422)

    resp = client.post("/api/groups", json={"name": "群1", "group_id": "g1", "platform": "dingtalk"})
    assert resp.status_code in (401, 422)

    resp = client.delete("/api/groups/1")
    assert resp.status_code in (401, 422)


def test_invalid_token(client, db_session):
    """Test that requests with invalid token fail."""
    invalid_auth = {"Authorization": "Bearer wrong-token"}
    resp = client.get("/api/groups", headers=invalid_auth)
    assert resp.status_code == 401
