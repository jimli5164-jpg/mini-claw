"""
时间工具模块

提供获取当前日期和时间功能。
"""

from datetime import datetime
from typing import Dict, Any

from agent.tools.base import Tool


class GetTimeTool(Tool):
    """
    获取当前时间工具
    
    返回当前的日期和时间，不需要任何参数。
    """
    
    @property
    def name(self) -> str:
        return "get_time"
    
    @property
    def description(self) -> str:
        return "获取当前的日期和时间"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    async def execute(self, **kwargs) -> str:
        """
        返回当前日期和时间
        
        返回：
            str: 当前日期和时间，格式为 YYYY-MM-DD HH:MM:SS (星期几)
        """
        now = datetime.now()
        # 格式：2024-01-15 14:30:25 (星期一)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S (%A)")
        return f"当前时间：{time_str}"