"""
渠道模块

提供不同消息渠道的实现。
"""

from .base import Channel
from .cli import CLIChannel

# FeishuChannel 延迟导入 — lark_oapi 不是必装依赖，
# 仅在飞书渠道启用时由 main.py 的 try/except 导入
__all__ = ["Channel", "CLIChannel"]
