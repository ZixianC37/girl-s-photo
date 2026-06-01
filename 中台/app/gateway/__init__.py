"""Event gateway for handling webhooks from Feishu and DingTalk"""
from app.gateway.dedup import EventDedup
from app.gateway import feishu, dingtalk

__all__ = ["EventDedup", "feishu", "dingtalk"]
