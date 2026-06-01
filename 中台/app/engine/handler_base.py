"""Base handler classes for task processing"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class TaskHandler(ABC):
    """Abstract base class defining the handler interface"""

    @abstractmethod
    def parse_event(self, event: Dict[str, Any], field_mapping: Dict[str, str]) -> Optional['TaskData']:
        """
        Parse incoming event into structured task data

        Args:
            event: Raw event from platform
            field_mapping: Mapping from event fields to task data fields

        Returns:
            TaskData object or None if parsing fails
        """
        pass

    @abstractmethod
    def get_flow(self) -> 'FlowDefinition':
        """
        Get the state machine flow definition for this task type

        Returns:
            FlowDefinition object
        """
        pass

    @abstractmethod
    def get_roles(self) -> 'RoleDefinition':
        """
        Get role definitions for this task type

        Returns:
            RoleDefinition object
        """
        pass

    @abstractmethod
    def build_card(self, task: 'TaskData', state: str) -> 'CardData':
        """
        Build a card for displaying task information

        Args:
            task: Task data
            state: Current flow state

        Returns:
            CardData object
        """
        pass

    @abstractmethod
    def get_reminder_rules(self) -> list:
        """
        Get reminder rules for this task type

        Returns:
            List of ReminderRule objects
        """
        pass

    @abstractmethod
    def handle_callback(self, action: str, user: str, task: 'TaskData') -> 'TaskUpdate':
        """
        Handle callback action from user interaction

        Args:
            action: Action identifier
            user: User who performed the action
            task: Current task data

        Returns:
            TaskUpdate object with status updates
        """
        pass


class BaseHandler(TaskHandler):
    """
    Base handler class with common functionality

    Subclasses should implement the abstract methods from TaskHandler.
    The handler_name is automatically set from the class name unless explicitly provided.
    """
    handler_name: str = ""

    def __init_subclass__(cls, **kwargs):
        """Auto-set handler_name from class name if not provided"""
        super().__init_subclass__(**kwargs)
        if not cls.handler_name:
            cls.handler_name = cls.__name__

    @classmethod
    def validate(cls) -> bool:
        """
        Validate handler configuration

        Returns:
            True if handler_name is set, False otherwise
        """
        return bool(cls.handler_name)
