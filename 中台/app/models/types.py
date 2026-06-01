from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class TaskData:
    """Parsed task data from event"""
    title: str
    participants: List[str]
    deadline: Optional[datetime] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CardAction:
    """A button/action in a card"""
    label: str
    action: str  # action identifier
    value: Optional[str] = None  # optional payload
    style: Optional[str] = None  # primary/danger/etc.


@dataclass
class CardSection:
    """A section within a card"""
    text: Optional[str] = None
    fields: Optional[List[Dict[str, Any]]] = None  # key-value pairs


@dataclass
class CardData:
    """Platform-independent card"""
    title: str
    sections: List[CardSection]
    actions: List[CardAction]
    subtitle: Optional[str] = None


@dataclass
class TaskUpdate:
    """Result of callback handling"""
    status: Optional[str] = None
    flow_state_update: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@dataclass
class FlowDefinition:
    """State machine definition"""
    states: List[str]
    initial: str
    transitions: Optional[Dict[str, Any]] = None  # state → allowed next states


@dataclass
class RoleDefinition:
    """Role definitions"""
    roles: List[str]  # role names
    default_role: str = "participant"


@dataclass
class ReminderRule:
    """Reminder rules"""
    trigger: str  # time_elapsed / percent_pending / manual
    target: str  # private / group / escalation
    message_template: str
    condition: Optional[Dict[str, Any]] = None  # extra conditions