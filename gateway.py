"""
网关模块

负责协调多个渠道和 Agent 实例之间的消息流转。
"""

import asyncio
from typing import Dict, List, Callable

from bus.queue import MessageBus, InboundMessage, OutboundMessage
from channels.base import Channel
from agent.loop import AgentLoop


class Gateway:
    """
    网关类
    
    负责协调多个渠道和 Agent 实例之间的消息流转。
    
    属性：
        bus: 消息总线
        channels: 渠道列表
        agent_factory: Agent 工厂函数
        _agents: Agent 实例缓存
        _channel_map: 渠道映射
    """
    
    def __init__(
        self,
        bus: MessageBus,
        channels: List[Channel],
        agent_factory: Callable[[str], AgentLoop]
    ):
        """
        初始化网关
        
        参数：
            bus: 消息总线
            channels: 渠道列表
            agent_factory: Agent 工厂函数（输入 session_key，返回 AgentLoop 实例）
        """
        self.bus = bus
        self.channels = channels
        self.agent_factory = agent_factory
        
        # 内部状态
        self._agents: Dict[str, AgentLoop] = {}
        self._channel_map: Dict[str, Channel] = {channel.name: channel for channel in channels}
    
    async def run(self):
        """
        启动网关
        
        并发启动所有渠道、入站处理循环和出站分发循环。
        """
        tasks = []
        
        print(f"[Gateway] 启动 {len(self.channels)} 个渠道...")
        print(f"[Gateway] bus 对象 id: {id(self.bus)}")
        
        # 启动所有渠道
        for channel in self.channels:
            print(f"[Gateway] 启动渠道: {channel.name}")
            tasks.append(asyncio.create_task(channel.start()))
        
        # 启动入站处理循环
        print("[Gateway] 启动入站处理循环...")
        tasks.append(asyncio.create_task(self._process_inbound()))
        
        # 启动出站分发循环
        print("[Gateway] 启动出站分发循环...")
        tasks.append(asyncio.create_task(self._dispatch_outbound()))
        
        # 并发运行所有任务
        print("[Gateway] 所有任务已启动")
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_inbound(self):
        """
        处理入站消息
        
        从消息总线消费入站消息，路由到对应的 Agent 处理。
        """
        print("[Gateway] _process_inbound 开始运行")
        while True:
            try:
                # 从消息总线获取入站消息
                print(f"[Gateway] 等待入站消息... (队列大小: {self.bus.inbound_queue.qsize()})")
                msg = await self.bus.consume_inbound()
                print(f"[Gateway] 收到入站消息: channel={msg.channel}, sender_id={msg.sender_id}, chat_id={msg.chat_id}, content={msg.content[:30]}...")
                
                # 构造会话键
                session_key = f"{msg.channel}:{msg.sender_id}"
                
                # 获取或创建 Agent 实例
                if session_key not in self._agents:
                    self._agents[session_key] = self.agent_factory(session_key)
                    print(f"[Gateway] 创建新 Agent 实例: {session_key}")
                
                agent = self._agents[session_key]
                
                # 调用 Agent 处理消息
                try:
                    print(f"[Gateway] 调用 Agent 处理消息...")
                    response = await agent.run(msg.content)
                    print(f"[Gateway] Agent 响应: {response[:50]}..." if response else "[Gateway] Agent 响应为空")
                except Exception as e:
                    response = f"处理消息时发生错误: {str(e)}"
                    print(f"[Gateway] Agent 错误: {e}")
                
                # 构造出站消息（透传 sender_id 和 chat_type 用于飞书 P2P 回复）
                outbound_msg = OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=response,
                    sender_id=getattr(msg, "sender_id", "") or "",
                    chat_type=getattr(msg, "chat_type", "") or "",
                )
                
                # 发布到消息总线
                print(f"[Gateway] 发布出站消息到消息总线: channel={outbound_msg.channel}, chat_id={outbound_msg.chat_id}")
                await self.bus.publish_outbound(outbound_msg)
                
            except Exception as e:
                print(f"[Gateway] 入站处理错误: {e}")

    async def _dispatch_outbound(self):
        """
        分发出站消息
        
        从消息总线消费出站消息，分发到对应的渠道。
        """
        while True:
            try:
                # 从消息总线获取出站消息
                msg = await self.bus.consume_outbound()
                print(f"[Gateway] 收到出站消息: channel={msg.channel}, chat_id={msg.chat_id}, content={msg.content[:30]}...")
                
                # 找到对应的渠道
                if msg.channel not in self._channel_map:
                    print(f"[Gateway] 未知渠道: {msg.channel}")
                    continue
                
                channel = self._channel_map[msg.channel]
                print(f"[Gateway] 分发消息到渠道: {channel.name}")
                
                # 发送消息
                await channel.send(msg)
                print(f"[Gateway] 消息发送成功")
                
            except Exception as e:
                print(f"[Gateway] 出站分发错误: {e}")
    
    async def shutdown(self):
        """
        关闭网关
        
        停止所有渠道，清空 Agent 缓存。
        """
        # 停止所有渠道
        for channel in self.channels:
            try:
                await channel.stop()
            except Exception as e:
                print(f"[Gateway] 停止渠道 {channel.name} 时出错: {e}")
        
        # 清空 Agent 缓存
        self._agents.clear()
        print("[Gateway] 已关闭")