"""
ToolRegistry 工具注册器模块

提供工具的注册、管理和执行功能，是 Agent 工具系统的核心管理器。
"""

from typing import Dict, List, Any
from agent.tools.base import Tool


class ToolRegistry:
    """
    工具注册器类
    
    负责管理所有工具的注册、查询和执行，提供统一的工具管理接口。
    
    属性：
        _tools: 内部存储工具的字典，key为工具名，value为Tool实例
    """
    
    def __init__(self):
        """初始化工具注册器，创建空的工具存储字典"""
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """
        注册一个工具
        
        参数：
            tool: Tool 实例，要注册的工具对象
        
        返回：
            None
        """
        self._tools[tool.name] = tool
    
    def get_definitions(self) -> List[Dict[str, Any]]:
        """
        获取所有已注册工具的 OpenAI 格式定义列表
        
        遍历所有工具，调用每个工具的 to_function_definition() 方法，
        将结果收集为列表返回。
        
        返回：
            list[dict]: 所有工具的 OpenAI 格式定义列表
        """
        return [tool.to_function_definition() for tool in self._tools.values()]
    
    async def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        异步执行指定工具
        
        根据工具名称查找工具并执行，如果工具不存在或执行出错，
        返回相应的错误信息。
        
        参数：
            name: str，工具名称
            arguments: dict，传递给工具的参数字典
        
        返回：
            str: 工具执行结果或错误信息
        """
        # 检查工具是否存在
        if name not in self._tools:
            return f"错误：工具 '{name}' 未找到"
        
        try:
            # 获取工具并执行
            tool = self._tools[name]
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            # 捕获执行异常并返回错误信息
            return f"执行工具 '{name}' 时发生错误: {str(e)}"
    
    def list_tools(self) -> List[str]:
        """
        获取所有已注册工具的名称列表
        
        返回：
            list[str]: 所有已注册工具的名称
        """
        return list(self._tools.keys())
