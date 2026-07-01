"""
CLI 渠道模块

实现命令行界面渠道，允许用户通过终端与 Agent 交互。
"""

import asyncio
from typing import List, Callable, Optional

from channels.base import Channel
from bus.queue import OutboundMessage, InboundMessage


class CLIChannel(Channel):
    """
    CLI 渠道类
    
    实现命令行界面渠道，允许用户通过终端与 Agent 交互。
    
    属性：
        tool_names: 工具名列表（由外部注入）
        _clear_callback: 清空历史回调（由外部注入）
        _response_event: 用于同步等待回复的事件
    """
    
    def __init__(self, bus):
        """
        初始化 CLI 渠道
        
        参数：
            bus: 消息总线实例
        """
        super().__init__("cli", bus)
        self._response_event = asyncio.Event()
        
        # 预留属性，由外部注入
        self.tool_names: List[str] = []
        self._clear_callback: Optional[Callable[[], None]] = None
    
    async def start(self):
        """
        启动 CLI 渠道
        
        进入主循环，读取用户输入并发布到消息总线。
        """
        print("\n进入交互式对话模式（输入 /exit 退出）")
        
        while True:
            try:
                # 使用 asyncio.to_thread 包装阻塞的 input()
                user_input = await asyncio.to_thread(input, ">>> ")
                user_input = user_input.strip()
                
                if user_input == "/exit":
                    print("退出对话")
                    break
                elif user_input == "/clear":
                    if self._clear_callback:
                        self._clear_callback()
                        print("历史记录已清空")
                    else:
                        print("未设置清空回调")
                    continue
                elif user_input == "/tools":
                    print("可用工具：")
                    for tool_name in self.tool_names:
                        print(f"  - {tool_name}")
                    continue
                elif not user_input:
                    continue
                
                # 构造入站消息
                inbound_msg = InboundMessage(
                    channel="cli",
                    sender_id="local",
                    chat_id="direct",
                    content=user_input
                )
                
                # 发布到消息总线
                await self.bus.publish_inbound(inbound_msg)
                
                # 等待回复完成
                await self._response_event.wait()
                self._response_event.clear()
                
            except EOFError:
                # stdin 已关闭（后台运行/管道模式），优雅退出
                print("\n[CLI] stdin 已关闭，退出交互模式")
                break
            except KeyboardInterrupt:
                print("\n用户中断，退出对话")
                break
            except Exception as e:
                print(f"发生错误：{e}")
    
    async def send(self, message: OutboundMessage):
        """
        发送消息到 CLI
        
        参数：
            message: 出站消息
        """
        print(f"🤖 {message.content}")
        # 通知 start() 可以继续了
        self._response_event.set()