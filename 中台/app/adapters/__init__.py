"""Message platform adapters for DingTalk, WeCom, etc."""

from .base import MessageAdapter
from .dingtalk_adapter import DingTalkAdapter
from .wecom_adapter import WeComAdapter

__all__ = ['MessageAdapter', 'DingTalkAdapter', 'WeComAdapter']
