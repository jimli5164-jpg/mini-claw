"""
Tool 抽象基类模块

该模块定义了一个通用的工具抽象基类，用于标准化 Agent 工具的接口。
所有具体的工具实现都应该继承此类，确保统一的调用方式和格式输出。

核心功能：
- 定义工具的基本属性（名称、描述、参数）
- 提供异步执行方法接口
- 自动生成 OpenAI 格式的工具定义 JSON
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Tool(ABC):
    """
    Tool 抽象基类
    
    所有工具类的基类，定义了工具必须实现的接口和通用方法。
    
    属性：
        name: 工具名称，用于标识和调用
        description: 工具功能描述，供 LLM 理解工具用途
        parameters: 工具参数定义，遵循 OpenAI 格式规范
    
    方法：
        execute: 异步执行工具的核心方法，由子类实现
        to_function_definition: 生成 OpenAI 格式的工具定义字典
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称，唯一标识符"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具功能描述，用于 LLM 理解工具用途"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        工具参数定义，遵循 OpenAI 工具调用格式
        
        参数结构示例：
        {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数1描述"
                },
                "param2": {
                    "type": "integer",
                    "description": "参数2描述"
                }
            },
            "required": ["param1"]
        }
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        异步执行工具的核心方法
        
        参数：
            **kwargs: 工具执行所需的关键字参数
        
        返回：
            str: 执行结果的字符串表示
        """
        pass
    
    def to_function_definition(self) -> Dict[str, Any]:
        """
        生成 OpenAI 格式的工具定义字典
        
        将工具的 name、description、parameters 组装成符合 OpenAI
        function calling 规范的 JSON 结构，便于 LLM 理解和调用。
        
        返回：
            dict: OpenAI 格式的工具定义
                  结构: {"type": "function", "function": {...}}
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
