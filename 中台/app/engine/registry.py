"""Handler registry for managing task handlers"""
import importlib
import importlib.util
import os
from pathlib import Path
from typing import Dict, Type, Optional, List
from app.engine.handler_base import BaseHandler


class HandlerRegistry:
    """
    Registry for managing task handler classes

    Supports manual registration and auto-discovery from a directory.
    """
    def __init__(self):
        self._handlers: Dict[str, Type[BaseHandler]] = {}

    def register(self, handler_cls: Type[BaseHandler]) -> None:
        """
        Register a handler class

        Args:
            handler_cls: Handler class to register

        Raises:
            ValueError: If handler name is already registered
        """
        if not hasattr(handler_cls, 'handler_name') or not handler_cls.handler_name:
            raise ValueError(f"Handler {handler_cls.__name__} must have a handler_name")

        handler_name = handler_cls.handler_name

        if handler_name in self._handlers:
            raise ValueError(f"Handler '{handler_name}' is already registered")

        self._handlers[handler_name] = handler_cls

    def get(self, name: str) -> Optional[Type[BaseHandler]]:
        """
        Get a handler class by name

        Args:
            name: Handler name

        Returns:
            Handler class or None if not found
        """
        return self._handlers.get(name)

    def list_handlers(self) -> List[str]:
        """
        Get list of registered handler names

        Returns:
            List of handler names
        """
        return list(self._handlers.keys())

    def auto_discover(self, handlers_dir: str) -> None:
        """
        Auto-discover and register handlers from a directory

        Scans the directory for Python files, imports them,
        and registers any BaseHandler subclasses found.

        Args:
            handlers_dir: Path to handlers directory

        Raises:
            ValueError: If duplicate handler names are found
        """
        handlers_path = Path(handlers_dir)

        if not handlers_path.exists():
            raise ValueError(f"Handlers directory does not exist: {handlers_dir}")

        # Find all Python files in the directory
        python_files = list(handlers_path.glob("*.py"))

        for py_file in python_files:
            # Skip __init__.py
            if py_file.name == "__init__.py":
                continue

            # Import the module
            module_name = py_file.stem
            spec = importlib.util.spec_from_file_location(module_name, py_file)

            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find BaseHandler subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # Check if it's a class and a subclass of BaseHandler (but not BaseHandler itself)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseHandler)
                    and attr is not BaseHandler
                ):
                    # Register the handler
                    self.register(attr)
