from app.services.identity import IdentityService


def test_get_platform_user_id(db_session):
    from app.models.tables import UserMapping
    mapping = UserMapping(feishu_user_id="f1", dingtalk_user_id="d1", phone="13800000001", name="Test")
    db_session.add(mapping)
    db_session.commit()

    svc = IdentityService(db_session)
    result = svc.get_platform_user_id(feishu_user_id="f1", platform="dingtalk")
    assert result == "d1"


def test_returns_none_when_no_mapping(db_session):
    svc = IdentityService(db_session)
    result = svc.get_platform_user_id(feishu_user_id="nonexistent", platform="dingtalk")
    assert result is None


def test_get_feishu_user_id(db_session):
    from app.models.tables import UserMapping
    mapping = UserMapping(feishu_user_id="f1", dingtalk_user_id="d1", phone="13800000001", name="Test")
    db_session.add(mapping)
    db_session.commit()

    svc = IdentityService(db_session)
    result = svc.get_feishu_user_id(platform_user_id="d1", platform="dingtalk")
    assert result == "f1"


def test_auto_match(db_session):
    from app.models.tables import UserMapping
    # Two partial mappings with same phone
    m1 = UserMapping(feishu_user_id="f1", phone="13800000001", name="User A")
    m2 = UserMapping(dingtalk_user_id="d1", phone="13800000001", name="User A")
    db_session.add_all([m1, m2])
    db_session.commit()

    svc = IdentityService(db_session)
    matched = svc.auto_match()
    assert matched >= 1

    # Verify the mapping is complete now
    result = svc.get_platform_user_id(feishu_user_id="f1", platform="dingtalk")
    assert result == "d1"
