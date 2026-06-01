import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.tables import RDProject, RDSubTask
from app.services.notification_chain import NotificationChain


@pytest.fixture
def mock_adapters():
    dt = MagicMock()
    dt.send_private_message = AsyncMock()
    dt.send_private_card = AsyncMock()
    dt.send_group_card = AsyncMock()
    return {"dingtalk": dt, "wecom": MagicMock()}


def _make_project(db_session, stages):
    p = RDProject(name="NotifTest", stages_snapshot=json.dumps(stages), status="active")
    db_session.add(p)
    db_session.flush()
    for idx, s in enumerate(stages):
        sub = RDSubTask(
            project_id=p.id, title=s["name"], assignees=json.dumps(s.get("default_assignees", [])),
            group_id="g1", platform="dingtalk", deliverables="[]",
            status="completed" if idx == 0 else "pending",
            sort_order=idx, stage_index=idx, stage_name=s["name"],
        )
        db_session.add(sub)
    db_session.commit()
    return p


def test_notify_next_stage_assignee(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
        {"name": "S1", "default_assignees": ["user_b"], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters)

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()
    call_args = mock_adapters["dingtalk"].send_private_message.call_args
    assert call_args[0][0] == "user_b"


def test_notify_manager(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "manager", "also_notify_manager": True}},
        {"name": "S1", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters, manager_user_id="manager_001")

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    # notify_type=="manager" sends one call, also_notify_manager sends a second
    assert mock_adapters["dingtalk"].send_private_message.call_count == 2
    for call_args in mock_adapters["dingtalk"].send_private_message.call_args_list:
        assert call_args[0][0] == "manager_001"


def test_notify_specific_group(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "specific_group", "group_name": "品鉴群"}},
        {"name": "S1", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters, group_lookup={"品鉴群": "group_pinjian"})

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()
    call_args = mock_adapters["dingtalk"].send_private_message.call_args
    assert call_args[0][0] == "group_pinjian"


def test_last_stage_notifies_manager(db_session, mock_adapters):
    stages = [
        {"name": "S0", "default_assignees": [], "notify_target": {"type": "next_stage_assignee"}},
    ]
    p = _make_project(db_session, stages)
    chain = NotificationChain(db_session, mock_adapters, manager_user_id="mgr")

    import asyncio
    asyncio.get_event_loop().run_until_complete(
        chain.on_stage_completed(p.id, 0)
    )

    mock_adapters["dingtalk"].send_private_message.assert_called_once()
    call_args = mock_adapters["dingtalk"].send_private_message.call_args
    assert call_args[0][0] == "mgr"
