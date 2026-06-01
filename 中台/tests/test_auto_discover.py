"""Test handler auto-discovery functionality"""
import tempfile
import os
import pytest
from pathlib import Path
from app.engine.registry import HandlerRegistry
from app.engine.handler_base import BaseHandler


def test_auto_discover_empty_directory():
    """Test auto-discover with empty directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = HandlerRegistry()
        registry.auto_discover(tmpdir)
        assert registry.list_handlers() == []


def test_auto_discover_with_handlers():
    """Test auto-discover finds and registers handlers"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test handler file
        handler_file = Path(tmpdir) / "test_handler.py"
        handler_content = """
from app.engine.handler_base import BaseHandler

class SampleHandler(BaseHandler):
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
"""
        handler_file.write_text(handler_content)

        # Test auto-discover
        registry = HandlerRegistry()
        registry.auto_discover(tmpdir)

        assert "SampleHandler" in registry.list_handlers()
        assert registry.get("SampleHandler") is not None


def test_auto_discover_ignores_init():
    """Test auto-discover ignores __init__.py"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create __init__.py with a handler class
        init_file = Path(tmpdir) / "__init__.py"
        init_content = """
from app.engine.handler_base import BaseHandler

class InitHandler(BaseHandler):
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
"""
        init_file.write_text(init_content)

        # Test auto-discover
        registry = HandlerRegistry()
        registry.auto_discover(tmpdir)

        # Should not register the handler from __init__.py
        assert "InitHandler" not in registry.list_handlers()


def test_auto_discover_duplicate_names():
    """Test auto-discover rejects duplicate handler names"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two handler files with same handler_name
        handler1_file = Path(tmpdir) / "handler1.py"
        handler1_content = """
from app.engine.handler_base import BaseHandler

class DuplicateHandler(BaseHandler):
    handler_name = "duplicate"

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
"""
        handler1_file.write_text(handler1_content)

        handler2_file = Path(tmpdir) / "handler2.py"
        handler2_content = """
from app.engine.handler_base import BaseHandler

class AnotherDuplicate(BaseHandler):
    handler_name = "duplicate"

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
"""
        handler2_file.write_text(handler2_content)

        # Test auto-discover raises ValueError
        registry = HandlerRegistry()
        with pytest.raises(ValueError, match="already registered"):
            registry.auto_discover(tmpdir)
