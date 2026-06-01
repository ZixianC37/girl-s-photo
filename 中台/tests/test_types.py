from sqlalchemy import inspect
from app.models.types import TaskData, CardData, CardSection, CardAction

def test_tables_created(db_engine):
    table_names = inspect(db_engine).get_table_names()
    assert "task_route" in table_names
    assert "task_instance" in table_names
    assert "task_participant" in table_names
    assert "file_record" in table_names
    assert "reminder_log" in table_names
    assert "user_mapping" in table_names

def test_task_data_construction():
    td = TaskData(title="Test Task", participants=["u1", "u2"], deadline=None, parameters={"key": "val"})
    assert td.title == "Test Task"
    assert len(td.participants) == 2

def test_card_data_construction():
    card = CardData(
        title="Card Title",
        subtitle="sub",
        sections=[CardSection(text="hello", fields=[{"k": "v"}])],
        actions=[CardAction(label="Click", action="confirm")]
    )
    assert card.actions[0].action == "confirm"
