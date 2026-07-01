"""
AgentLoop 代理循环模块

实现 Agent 的核心推理循环，处理工具调用和对话流程。
"""

from typing import List, Dict, Any, Optional

from agent.providers.base import LLMProvider, LLMResponse
from agent.tools.registry import ToolRegistry
from agent.context import ContextBuilder


class AgentLoop:
    """
    Agent 核心循环类
    
    负责管理对话历史、调用 LLM、执行工具调用、控制循环流程。
    
    属性：
        provider: LLM 提供者
        tool_registry: 工具注册器
        context_builder: 上下文构建器
        model: 模型名称
        max_iterations: 最大迭代次数
        history: 对话历史
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        context_builder: ContextBuilder,
        model: str,
        max_iterations: int = 32
    ):
        """
        初始化 Agent 循环
        
        参数：
            provider: LLM 提供者
            tool_registry: 工具注册器
            context_builder: 上下文构建器
            model: 模型名称
            max_iterations: 最大迭代次数
        """
        self.provider = provider
        self.tool_registry = tool_registry
        self.context_builder = context_builder
        self.model = model
        self.max_iterations = max_iterations
        self.history: List[Dict[str, str]] = []
    
    async def run(self, user_input: str) -> str:
        """
        执行一次完整的 Agent 推理循环
        
        参数：
            user_input: 用户输入
            
        返回：
            str: 最终回复内容
        """
        # 构建消息列表（系统提示词 + 历史 + 当前输入）
        messages = self.context_builder.build_messages(
            history=self.history,
            current_message=user_input
        )
        
        for iteration in range(self.max_iterations):
            # 获取工具定义
            tools = self.tool_registry.get_definitions()
            print(f"[DEBUG] 迭代 {iteration+1}: 可用工具 {len(tools)} 个")
            
            # 调用 LLM
            response = await self.provider.chat(
                messages=messages,
                tools=tools,
                model=self.model
            )
            
            print(f"[DEBUG] LLM 响应: has_tool_calls={response.has_tool_calls}, finish_reason={response.finish_reason}")
            
            # 提取并显示思考过程（只显示思考部分，不显示最终回复）
            if response.content and "【思考】" in response.content:
                thinking_start = response.content.find("【思考】")
                thinking_end = response.content.find("\n", thinking_start)
                if thinking_end == -1:
                    thinking_end = len(response.content)
                thinking_end_tag = response.content.find("【/思考】", thinking_start)
                if thinking_end_tag != -1 and thinking_end_tag < thinking_end:
                    thinking_end = thinking_end_tag
                thinking = response.content[thinking_start:thinking_end].strip()
                print(f"\n🤔 {thinking}")
            
            if response.tool_calls:
                print(f"🔧 工具调用: {[(tc.name, tc.arguments) for tc in response.tool_calls]}")
            
            # 如果没有工具调用，直接返回
            if not response.has_tool_calls:
                if response.content:
                    # 更新历史（只保留用户和助手消息）
                    self.history.append({"role": "user", "content": user_input})
                    self.history.append({"role": "assistant", "content": response.content})
                return response.content or "未收到回复"
            
            # 执行工具调用
            tool_results = []
            
            # 构建助手消息（包含工具调用信息）
            import json
            assistant_message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
            }
            
            for tool_call in response.tool_calls:
                result = await self.tool_registry.execute(
                    name=tool_call.name,
                    arguments=tool_call.arguments
                )
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # 将工具调用和结果添加到消息列表（用于下一次迭代）
            messages.append(assistant_message)
            messages.extend(tool_results)
            
            # 更新历史（添加工具调用结果，用于后续对话）
            self.history.append({"role": "assistant", "content": f"已执行工具调用: {[tc.name for tc in response.tool_calls]}"})
            
        return f"达到最大迭代次数 ({self.max_iterations})，自动终止"
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.history = []
    
    def get_tool_list(self) -> List[str]:
        """获取已注册的工具列表"""
        return self.tool_registry.list_tools()