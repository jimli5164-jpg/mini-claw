"""
Shell 命令执行工具模块

提供在指定工作目录下执行 Shell 命令的功能，包含多层安全防护机制。
安全策略：
- 正则匹配拦截危险命令模式（删除、格式化、权限提升等）
- 60 秒执行超时限制
- 输出长度截断（10000 字符）
"""

import asyncio
import os
import re
from typing import Dict, Any, Optional

from agent.tools.base import Tool


class ExecTool(Tool):
    """
    Shell 命令执行工具

    在指定工作目录下执行 Shell 命令，返回标准输出和错误输出。
    内置危险命令拦截和超时保护。

    属性：
        workspace: 命令执行的工作目录（绝对路径）
        deny_patterns: 危险命令正则表达式列表
    """

    def __init__(self, workspace: str = "."):
        """
        初始化 Shell 命令执行工具

        参数：
            workspace: 工作目录，命令在此目录下执行
        """
        self.workspace = os.path.abspath(workspace)
        self.deny_patterns = [
            # 递归删除
            r"rm\s+.*-r",
            r"rm\s+-rf",
            # Windows 递归删除
            r"rmdir\s+/s",
            # 格式化磁盘
            r"format\s+",
            # Linux 格式化
            r"\bmkfs\b",
            # 关机重启
            r"\bshutdown\b",
            r"\breboot\b",
            # 权限提升
            r"sudo\s+",
            r"\bsu\b",
            # 危险权限修改
            r"chmod\s+777",
            # 覆盖设备文件
            r">\s*/dev/",
            # 下载执行恶意脚本
            r"wget\s+.*\|\s*sh",
            r"curl\s+.*\|\s*bash",
            # 开网络后门
            r"\bnc\s+-l",
            r"\bncat\s+-l",
            # 磁盘镜像覆写
            r"\bdd\s+if=",
            # Fork 炸弹
            r":\(\)\{.*\}",
        ]

    @property
    def name(self) -> str:
        """工具名称"""
        return "exec"

    @property
    def description(self) -> str:
        """工具功能描述"""
        return (
            "在指定工作目录下执行 Shell 命令并返回输出结果。"
            "支持标准输出和标准错误捕获，内置超时和安全拦截机制。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """工具参数定义"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 Shell 命令"
                }
            },
            "required": ["command"]
        }

    def _is_dangerous(self, command: str) -> Optional[str]:
        """
        检查命令是否包含危险模式

        参数：
            command: 用户输入的命令字符串

        返回：
            Optional[str]: 如果命中危险模式返回拦截信息，否则返回 None
        """
        for pattern in self.deny_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return f"安全拦截：检测到危险命令模式 '{pattern}'"
        return None

    async def execute(self, **kwargs) -> str:
        """
        执行 Shell 命令

        流程：
        1. 检查命令安全性
        2. 在工作目录下创建子进程执行命令
        3. 设置 60 秒超时
        4. 收集 stdout 和 stderr
        5. 截断超长输出
        6. 返回执行结果（含退出码）

        参数：
            command: 要执行的 Shell 命令

        返回：
            str: 命令执行结果（输出 + 退出码）
        """
        command = kwargs.get("command", "")

        # 步骤 1：安全检查
        danger_msg = self._is_dangerous(command)
        if danger_msg:
            return danger_msg

        try:
            # 步骤 2：创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace
            )

            # 步骤 3：设置超时等待
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return "命令执行超时（60秒），已终止"

            # 步骤 4：拼接输出
            stdout_text = stdout_data.decode("utf-8", errors="replace")
            stderr_text = stderr_data.decode("utf-8", errors="replace")

            output_parts = []
            if stdout_text:
                output_parts.append(stdout_text)
            if stderr_text:
                output_parts.append(f"标准错误:\n{stderr_text}")

            result = "\n".join(output_parts)

            # 步骤 5：截断超长输出
            max_length = 10000
            if len(result) > max_length:
                result = result[:max_length] + "\n...(输出过长，已截断)"

            # 步骤 6：添加退出码
            result += f"\n[退出码: {process.returncode}]"

            return result

        except Exception as e:
            return f"命令执行失败: {type(e).__name__}: {str(e)}"
