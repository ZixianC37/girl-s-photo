"""Tests for handler registry system"""
import pytest
from app.engine.registry import HandlerRegistry


def test_registry_empty_initially():
    """Test that a new registry is empty"""
    reg = HandlerRegistry()
    assert reg.list_handlers() == []


def test_registry_registers_handler():
    """Test that a handler can be registered"""
    from app.engine.handler_base import BaseHandler

    class TestHandler(BaseHandler):
        def parse_event(self, event, field_mapping):
            return None

        def get_flow(self):
            return None

        def get_roles(self):
            return None

        def build_card(self, task, state):
            return None

        def get_reminder_rules(self):
            return None

        def handle_callback(self, action, user, task):
            return None

    reg = HandlerRegistry()
    reg.register(TestHandler)
    assert "TestHandler" in reg.list_handlers()


def test_registry_rejects_duplicate():
    """Test that duplicate handler names are rejected"""
    from app.engine.handler_base import BaseHandler

    class TestHandler(BaseHandler):
        def parse_event(self, event, field_mapping):
            return None

        def get_flow(self):
            return None

        def get_roles(self):
            return None

        def build_card(self, task, state):
            return None

        def get_reminder_rules(self):
            return None

        def handle_callback(self, action, user, task):
            return None

    reg = HandlerRegistry()
    reg.register(TestHandler)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(TestHandler)


def test_registry_get_handler():
    """Test retrieving a handler by name"""
    from app.engine.handler_base import BaseHandler

    class TestHandler(BaseHandler):
        def parse_event(self, event, field_mapping):
            return None

        def get_flow(self):
            return None

        def get_roles(self):
            return None

        def build_card(self, task, state):
            return None

        def get_reminder_rules(self):
            return None

        def handle_callback(self, action, user, task):
            return None

    reg = HandlerRegistry()
    reg.register(TestHandler)
    assert reg.get("TestHandler") is TestHandler


def test_registry_get_nonexistent_handler():
    """Test retrieving a non-existent handler returns None"""
    reg = HandlerRegistry()
    assert reg.get("NonexistentHandler") is None


def test_base_handler_auto_naming():
    """Test that BaseHandler auto-sets handler_name from class name"""
    from app.engine.handler_base import BaseHandler

    class MyCustomHandler(BaseHandler):
        def parse_event(self, event, field_mapping):
            return None

        def get_flow(self):
            return None

        def get_roles(self):
            return None

        def build_card(self, task, state):
            return None

        def get_reminder_rules(self):
            return None

        def handle_callback(self, action, user, task):
            return None

    assert MyCustomHandler.handler_name == "MyCustomHandler"


def test_base_handler_custom_name():
    """Test that BaseHandler respects custom handler_name"""
    from app.engine.handler_base import BaseHandler

    class CustomNameHandler(BaseHandler):
        handler_name = "custom_name"

        def parse_event(self, event, field_mapping):
            return None

        def get_flow(self):
            return None

        def get_roles(self):
            return None

        def build_card(self, task, state):
            return None

        def get_reminder_rules(self):
            return None

        def handle_callback(self, action, user, task):
            return None

    assert CustomNameHandler.handler_name == "custom_name"


def test_base_handler_validate():
    """Test BaseHandler validate classmethod"""
    from app.engine.handler_base import BaseHandler

    class ValidHandler(BaseHandler):
        def parse_event(self, event, field_mapping):
            return None

        def get_flow(self):
            return None

        def get_roles(self):
            return None

        def build_card(self, task, state):
            return None

        def get_reminder_rules(self):
            return None

        def handle_callback(self, action, user, task):
            return None

    assert ValidHandler.validate() is True
