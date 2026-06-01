# tests/test_admin_api.py

AUTH_HEADERS = {"Authorization": "Bearer changeme"}

def test_list_routes_empty(client):
    resp = client.get("/api/routes", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []

def test_create_route(client, db_session):
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_1",
        "platform": "dingtalk",
        "group_id": "group_1",
        "field_mapping": {"title": "task_title"},
        "enabled": True
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["handler_name"] == "TestHandler"

def test_update_route(client, db_session):
    # Create first
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_1",
        "platform": "dingtalk",
        "group_id": "group_1",
        "field_mapping": {},
        "enabled": True
    }, headers=AUTH_HEADERS)
    route_id = resp.json()["id"]

    # Update
    resp = client.put(f"/api/routes/{route_id}", json={"enabled": False}, headers=AUTH_HEADERS)
    assert resp.status_code == 200

def test_delete_route(client, db_session):
    resp = client.post("/api/routes", json={
        "handler_name": "TestHandler",
        "feishu_table_id": "tbl_1",
        "platform": "dingtalk",
        "group_id": "group_1",
        "field_mapping": {},
        "enabled": True
    }, headers=AUTH_HEADERS)
    route_id = resp.json()["id"]

    resp = client.delete(f"/api/routes/{route_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 200

    # Verify deleted
    resp = client.get("/api/routes", headers=AUTH_HEADERS)
    assert resp.json() == []

def test_auth_required(client):
    resp = client.get("/api/routes")
    assert resp.status_code == 422  # Missing header

def test_invalid_token(client):
    resp = client.get("/api/routes", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401

def test_list_handlers(client):
    resp = client.get("/api/handlers", headers=AUTH_HEADERS)
    assert resp.status_code == 200
