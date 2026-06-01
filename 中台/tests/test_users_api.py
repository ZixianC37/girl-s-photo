import pytest
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer changeme"}


def test_list_users(client: TestClient, db_session):
    """Test listing users without filters"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f1",
        dingtalk_user_id="d1",
        phone="13800000001",
        name="张三"
    ))
    db_session.commit()

    resp = client.get("/api/users", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["sync_status"] == "matched"
    assert "****" in data["items"][0]["phone"]
    assert data["items"][0]["phone"] == "138****0001"


def test_list_users_filter_unmatched(client: TestClient, db_session):
    """Test filtering unmatched users"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f2",
        phone="13800000002",
        name="李四"
    ))
    db_session.commit()

    resp = client.get("/api/users?status=unmatched", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["sync_status"] == "unmatched"


def test_list_users_filter_matched(client: TestClient, db_session):
    """Test filtering matched users"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f3",
        dingtalk_user_id="d3",
        phone="13800000003",
        name="王五"
    ))
    db_session.add(UserMapping(
        feishu_user_id="f4",
        phone="13800000004",
        name="赵六"
    ))
    db_session.commit()

    resp = client.get("/api/users?status=matched", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["sync_status"] == "matched"


def test_list_users_search_by_name(client: TestClient, db_session):
    """Test searching users by name"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f5",
        phone="13800000005",
        name="张三"
    ))
    db_session.add(UserMapping(
        feishu_user_id="f6",
        phone="13800000006",
        name="李四"
    ))
    db_session.commit()

    resp = client.get("/api/users?search=张三", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "张三"


def test_list_users_search_by_phone(client: TestClient, db_session):
    """Test searching users by phone"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f7",
        phone="13800000007",
        name="王五"
    ))
    db_session.add(UserMapping(
        feishu_user_id="f8",
        phone="13900000008",
        name="赵六"
    ))
    db_session.commit()

    resp = client.get("/api/users?search=13800000007", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["phone"] == "138****0007"


def test_list_users_pagination(client: TestClient, db_session):
    """Test pagination"""
    from app.models.tables import UserMapping
    for i in range(25):
        db_session.add(UserMapping(
            feishu_user_id=f"f{i}",
            phone=f"1380000{i:03d}",
            name=f"用户{i}"
        ))
    db_session.commit()

    resp = client.get("/api/users?page=2&page_size=10", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 25
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert len(data["items"]) == 10


def test_update_user(client: TestClient, db_session):
    """Test updating user fields"""
    from app.models.tables import UserMapping
    m = UserMapping(
        feishu_user_id="f9",
        phone="13800000009",
        name="王五"
    )
    db_session.add(m)
    db_session.commit()
    uid = db_session.query(UserMapping).first().id

    resp = client.put(
        f"/api/users/{uid}",
        json={"dingtalk_user_id": "d9"},
        headers=AUTH
    )
    assert resp.status_code == 200

    # Verify the update
    db_session.refresh(m)
    assert m.dingtalk_user_id == "d9"
    assert m.feishu_user_id == "f9"  # Original value preserved


def test_update_user_multiple_fields(client: TestClient, db_session):
    """Test updating multiple user fields"""
    from app.models.tables import UserMapping
    m = UserMapping(
        feishu_user_id="f10",
        phone="13800000010",
        name="赵六"
    )
    db_session.add(m)
    db_session.commit()
    uid = db_session.query(UserMapping).first().id

    resp = client.put(
        f"/api/users/{uid}",
        json={
            "dingtalk_user_id": "d10",
            "wecom_user_id": "w10",
            "name": "赵六更新"
        },
        headers=AUTH
    )
    assert resp.status_code == 200

    # Verify the updates
    db_session.refresh(m)
    assert m.dingtalk_user_id == "d10"
    assert m.wecom_user_id == "w10"
    assert m.name == "赵六更新"


def test_update_user_not_found(client: TestClient, db_session):
    """Test updating non-existent user"""
    resp = client.put(
        "/api/users/99999",
        json={"dingtalk_user_id": "d999"},
        headers=AUTH
    )
    assert resp.status_code == 404


def test_sync_users(client: TestClient, db_session):
    """Test user sync endpoint"""
    from app.models.tables import UserMapping
    # Add two users with same phone but different platform IDs
    db_session.add(UserMapping(
        feishu_user_id="f11",
        phone="13800000011"
    ))
    db_session.add(UserMapping(
        dingtalk_user_id="d11",
        phone="13800000011"
    ))
    db_session.commit()

    resp = client.post("/api/users/sync", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced"] >= 1
    assert "total" in data


def test_sync_users_no_matches(client: TestClient, db_session):
    """Test sync when no matches are possible"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f12",
        phone="13800000012"
    ))
    db_session.commit()

    resp = client.post("/api/users/sync", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    # No matches should be made
    assert data["synced"] == 0
    assert data["total"] >= 1


def test_unauthorized_access(client: TestClient):
    """Test that unauthorized access is denied"""
    resp = client.get("/api/users")
    # FastAPI returns 422 for missing required headers
    assert resp.status_code == 422

    resp = client.get("/api/users", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


def test_phone_masking(client: TestClient, db_session):
    """Test that phone numbers are properly masked"""
    from app.models.tables import UserMapping
    db_session.add(UserMapping(
        feishu_user_id="f13",
        phone="13800001313",
        name="测试用户"
    ))
    db_session.add(UserMapping(
        feishu_user_id="f14",
        name="无手机用户"
    ))
    db_session.commit()

    resp = client.get("/api/users", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()

    # Find the user with phone
    user_with_phone = next(u for u in data["items"] if u["name"] == "测试用户")
    assert user_with_phone["phone"] == "138****1313"

    # Find the user without phone
    user_no_phone = next(u for u in data["items"] if u["name"] == "无手机用户")
    assert user_no_phone["phone"] is None
