"""
LLM Provider 基础模块

定义 LLM 服务提供者的核心数据结构和抽象接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ToolCallRequest:
    """
    工具调用请求数据类
    
    封装 LLM 返回的工具调用信息，包括工具名称、参数和可选的推理过程。
    
    字段：
        id: 工具调用的唯一标识
        name: 要调用的工具名称
        arguments: 传递给工具的参数字典
        reasoning_content: 模型生成的推理过程（部分模型支持，如 Kimi-K2.5、DeepSeek-R1）
    """
    id: str
    name: str
    arguments: Dict[str, Any]
    reasoning_content: Optional[str] = None


@dataclass
class LLMResponse:
    """
    LLM 响应数据类
    
    封装 LLM 返回的响应内容，包括文本回复、工具调用列表和使用统计。
    
    字段：
        content: LLM 返回的文本内容，None 表示没有文本回复（只有工具调用）
        tool_calls: 工具调用请求列表
        finish_reason: 响应结束原因，默认为 "stop"
        usage: API 使用统计信息，默认为空字典
    """
    content: Optional[str] = None
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_tool_calls(self) -> bool:
        """
        检查是否包含工具调用
        
        返回：
            bool: 如果 tool_calls 列表非空返回 True，否则返回 False
        """
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    LLM 提供者抽象基类
    
    定义所有 LLM 服务提供者必须实现的接口，统一不同 LLM 服务的调用方式。
    
    方法：
        chat: 异步聊天方法，发送消息给 LLM 并返回响应
    """
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        异步发送聊天消息给 LLM
        
        参数：
            messages: 消息列表，每个消息为字典，包含 role 和 content 字段
            tools: 可选的工具定义列表，用于工具调用
            model: 可选的模型名称，指定使用的 LLM 模型
        
        返回：
            LLMResponse: LLM 的响应对象
        """
        pass
