"""
消息总线模块

提供跨渠道消息的统一传递机制。
"""

from .queue import InboundMessage, OutboundMessage, MessageBus

__all__ = ["InboundMessage", "OutboundMessage", "MessageBus"]