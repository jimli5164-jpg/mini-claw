"""
消息总线模块

提供跨渠道消息的统一传递机制，支持异步消息队列。
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class InboundMessage:
    """
    入站消息类

    表示从外部渠道收到的消息。

    属性：
        channel: 来源渠道名称，如 "feishu"、"qq"、"web"、"cli"
        sender_id: 发送者标识
        chat_id: 会话标识，群聊或私聊
        content: 消息正文
        raw: 原始消息，调试用
        chat_type: 聊天类型，如 "p2p"（私聊）、"group"（群聊），可选
    """
    channel: str
    sender_id: str
    chat_id: str
    content: str
    raw: Optional[Dict] = None
    chat_type: str = ""


@dataclass
class OutboundMessage:
    """
    出站消息类

    表示要发送到外部渠道的消息。

    属性：
        channel: 目标渠道
        chat_id: 目标会话
        content: 回复正文
        reply_to: 引用的消息 ID，可选
        sender_id: 发送者标识（用于 P2P 回复），可选
        chat_type: 聊天类型（"p2p" 或 "group"），可选
    """
    channel: str
    chat_id: str
    content: str
    reply_to: Optional[str] = None
    sender_id: str = ""
    chat_type: str = ""


class MessageBus:
    """
    消息总线类
    
    提供异步消息队列，用于在不同组件之间传递消息。
    
    属性：
        inbound_queue: 入站消息队列
        outbound_queue: 出站消息队列
    """
    
    def __init__(self):
        """
        初始化消息总线
        
        创建两个 asyncio.Queue 用于入站和出站消息。
        """
        self.inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound_queue: asyncio.Queue[OutboundMessage] = asyncio.Queue()
    
    async def publish_inbound(self, msg: InboundMessage):
        """
        发布入站消息
        
        将消息放入入站队列。
        
        参数：
            msg: 入站消息
        """
        await self.inbound_queue.put(msg)
    
    async def consume_inbound(self) -> InboundMessage:
        """
        消费入站消息
        
        从入站队列取出消息，会自动等待直到有消息。
        
        返回：
            InboundMessage: 入站消息
        """
        return await self.inbound_queue.get()
    
    async def publish_outbound(self, msg: OutboundMessage):
        """
        发布出站消息
        
        将消息放入出站队列。
        
        参数：
            msg: 出站消息
        """
        await self.outbound_queue.put(msg)
    
    async def consume_outbound(self) -> OutboundMessage:
        """
        消费出站消息
        
        从出站队列取出消息，会自动等待直到有消息。
        
        返回：
            OutboundMessage: 出站消息
        """
        return await self.outbound_queue.get()