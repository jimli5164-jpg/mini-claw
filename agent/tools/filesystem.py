"""
文件系统工具模块

提供文件读取、写入和目录列表功能，包含安全路径检查机制。
"""

import os
from abc import ABC
from typing import Dict, Any

from agent.tools.base import Tool


class BaseFileSystemTool(Tool, ABC):
    """
    文件系统工具基类
    
    提供统一的路径安全检查功能，防止路径穿越攻击。
    
    属性：
        workspace: 工作区根目录，所有操作必须在该目录内进行
    """
    
    def __init__(self, workspace: str):
        """
        初始化文件系统工具
        
        参数：
            workspace: 工作区根目录路径
        """
        self.workspace = os.path.abspath(workspace)
    
    def _safe_path(self, user_input_path: str) -> str:
        """
        安全路径检查
        
        将用户输入的路径与工作区拼接，检查是否在工作区内，防止路径穿越攻击。
        
        参数：
            user_input_path: 用户输入的路径
            
        返回：
            str: 安全的绝对路径，或 "拦截" 表示路径非法
        """
        absolute_path = os.path.abspath(os.path.join(self.workspace, user_input_path))
        if not absolute_path.startswith(self.workspace):
            return "拦截"
        return absolute_path


class ReadFileTool(BaseFileSystemTool):
    """
    文件读取工具
    
    读取指定文件的内容，包含安全路径检查和内容截断机制。
    """
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "读取指定文件的内容"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径（相对于工作区）"
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, **kwargs) -> str:
        """
        读取文件内容
        
        参数：
            file_path: 要读取的文件路径
            
        返回：
            str: 文件内容，超过 16000 字符时截断；路径非法或文件不存在时返回错误信息
        """
        file_path = kwargs.get("file_path")
        
        if not file_path:
            return "错误：缺少 file_path 参数"
        
        # 安全路径检查
        safe_path = self._safe_path(file_path)
        if safe_path == "拦截":
            return "错误：非法路径访问被拦截"
        
        # 检查文件是否存在
        if not os.path.exists(safe_path):
            return f"错误：文件 '{file_path}' 不存在"
        
        # 检查是否为文件
        if not os.path.isfile(safe_path):
            return f"错误：'{file_path}' 不是文件"
        
        try:
            # 读取文件内容
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 超过 16000 字符时截断
            max_chars = 16000
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n[内容已截断，共 {len(content)} 字符]"
            
            return content
        except Exception as e:
            return f"读取文件时发生错误: {str(e)}"


class WriteFileTool(BaseFileSystemTool):
    """
    文件写入工具
    
    将内容写入指定文件，自动创建父目录，包含安全路径检查。
    """
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "将内容写入指定文件，自动创建父目录"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件路径（相对于工作区）"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容"
                }
            },
            "required": ["file_path", "content"]
        }
    
    async def execute(self, **kwargs) -> str:
        """
        写入文件内容
        
        参数：
            file_path: 要写入的文件路径
            content: 要写入的内容
            
        返回：
            str: 操作结果消息
        """
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        
        if not file_path:
            return "错误：缺少 file_path 参数"
        
        if content is None:
            return "错误：缺少 content 参数"
        
        # 安全路径检查
        safe_path = self._safe_path(file_path)
        if safe_path == "拦截":
            return "错误：非法路径访问被拦截"
        
        try:
            # 自动创建父目录
            parent_dir = os.path.dirname(safe_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # 写入文件
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"文件 '{file_path}' 写入成功"
        except Exception as e:
            return f"写入文件时发生错误: {str(e)}"


class ListDirTool(BaseFileSystemTool):
    """
    目录列表工具
    
    列出指定目录的内容，显示文件名+大小，目录名+"/"后缀，按名称排序。
    """
    
    @property
    def name(self) -> str:
        return "list_dir"
    
    @property
    def description(self) -> str:
        return "列出指定目录的内容，显示文件大小和目录标识"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "要列出的目录路径（相对于工作区），默认为当前目录"
                }
            },
            "required": []
        }
    
    async def execute(self, **kwargs) -> str:
        """
        列出目录内容
        
        参数：
            dir_path: 要列出的目录路径，默认为空（当前目录）
            
        返回：
            str: 目录内容列表，包含文件名/目录名和大小信息
        """
        dir_path = kwargs.get("dir_path", "")
        
        # 安全路径检查
        safe_path = self._safe_path(dir_path)
        if safe_path == "拦截":
            return "错误：非法路径访问被拦截"
        
        # 检查目录是否存在
        if not os.path.exists(safe_path):
            return f"错误：目录 '{dir_path}' 不存在"
        
        # 检查是否为目录
        if not os.path.isdir(safe_path):
            return f"错误：'{dir_path}' 不是目录"
        
        try:
            # 获取目录内容
            entries = os.listdir(safe_path)
            # 按名称排序
            entries.sort()
            
            result_lines = []
            for entry in entries:
                entry_path = os.path.join(safe_path, entry)
                if os.path.isdir(entry_path):
                    # 目录：名称 + "/"
                    result_lines.append(f"{entry}/")
                else:
                    # 文件：名称 + 大小
                    size = os.path.getsize(entry_path)
                    result_lines.append(f"{entry} ({size} bytes)")
            
            return "\n".join(result_lines)
        except Exception as e:
            return f"列出目录时发生错误: {str(e)}"
