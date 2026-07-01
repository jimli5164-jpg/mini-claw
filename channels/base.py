"""
渠道抽象基类模块

定义所有渠道必须实现的接口。
"""

from abc import ABC, abstractmethod
from bus.queue import MessageBus, OutboundMessage


class Channel(ABC):
    """
    渠道抽象基类
    
    定义所有渠道必须实现的接口。
    
    属性：
        name: 渠道名称
        bus: 消息总线实例
    """
    
    def __init__(self, name: str, bus: MessageBus):
        """
        初始化渠道
        
        参数：
            name: 渠道名称
            bus: 消息总线实例
        """
        self.name = name
        self.bus = bus
    
    @abstractmethod
    async def start(self):
        """
        启动渠道
        
        开始监听消息或处理渠道相关任务。
        """
        pass
    
    @abstractmethod
    async def send(self, message: OutboundMessage):
        """
        发送消息
        
        参数：
            message: 出站消息
        """
        pass
    
    async def stop(self):
        """
        停止渠道（可选覆盖）
        
        清理资源、关闭连接等。
        """
        pass