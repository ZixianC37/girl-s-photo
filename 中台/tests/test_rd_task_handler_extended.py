"""Extended tests for RDTaskHandler rework and report-problem support."""
from app.handlers.rd_task_handler import RDTaskHandler


def test_handle_callback_rework():
    handler = RDTaskHandler()
    from app.models.types import TaskUpdate

    update = handler.handle_callback("rework", "user_a", None)
    assert update.status == "submitted"
    assert update.flow_state_update is not None
    assert update.flow_state_update.get("rework_by") == "user_a"


def test_handle_callback_report_problem():
    handler = RDTaskHandler()

    update = handler.handle_callback("report_problem", "user_b", None)
    assert update.status == "submitted"
    assert update.flow_state_update is not None
    assert update.flow_state_update.get("reported_problem_by") == "user_b"


def test_handle_callback_confirm():
    handler = RDTaskHandler()

    update = handler.handle_callback("confirm", "user_a", None)
    assert update.status == "confirmed"


def test_build_card_rework_state():
    handler = RDTaskHandler()
    from app.models.types import CardData
    from unittest.mock import MagicMock

    mock_task = MagicMock()
    mock_task.flow_state = '{"title": "Test", "rework_by": "user_a"}'
    mock_task.deadline = None

    card = handler.build_card(mock_task, "rework")
    assert isinstance(card, CardData)


def test_build_card_with_problem_report_button():
    handler = RDTaskHandler()
    from app.models.types import CardData
    from unittest.mock import MagicMock

    mock_task = MagicMock()
    mock_task.flow_state = '{"title": "Test"}'
    mock_task.deadline = None

    card = handler.build_card(mock_task, "pending")
    action_labels = [a.label for a in card.actions]
    assert "确认接单" in action_labels
    assert "上报问题" in action_labels
