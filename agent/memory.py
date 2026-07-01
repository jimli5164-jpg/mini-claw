"""
记忆整合器模块

负责对话历史的压缩和记忆管理，当历史消息过多时自动生成摘要。
"""

import json
import os
from datetime import datetime
from typing import List, Dict

from agent.providers.base import LLMProvider


class MemoryConsolidator:
    """
    记忆整合器类

    负责对话历史的压缩和记忆管理，当历史消息过多时自动生成摘要。

    属性：
        provider: LLM 提供者，用于生成摘要
        workspace: 工作区路径
        token_budget: Token 预算，超过时触发压缩
    """

    def __init__(
        self,
        provider: LLMProvider,
        workspace: str,
        token_budget: int = 6000
    ):
        """
        初始化记忆整合器

        参数：
            provider: LLMProvider 实例
            workspace: 工作区路径
            token_budget: Token 预算，默认 6000
        """
        self.provider = provider
        self.workspace = workspace
        self.token_budget = token_budget

        # 确保 memory 目录存在
        self._memory_dir = os.path.join(workspace, "memory")
        os.makedirs(self._memory_dir, exist_ok=True)

    def estimate_tokens(self, messages: List[Dict]) -> int:
        """
        估算消息的 Token 数量

        参数：
            messages: 消息列表

        返回：
            int: 估算的总 Token 数
        """
        total_tokens = 0
        for msg in messages:
            # 粗略估算：每个字符约等于 0.5 Token
            total_tokens += len(json.dumps(msg, ensure_ascii=False)) // 2
        return total_tokens

    async def maybe_consolidate(self, messages: List[Dict]) -> List[Dict]:
        """
        可能压缩消息列表

        如果消息的 Token 数超过预算，则进行压缩。

        参数：
            messages: 消息列表

        返回：
            List[Dict]: 压缩后的消息列表
        """
        # 估算当前消息的 Token 数
        token_count = self.estimate_tokens(messages)

        # 如果 Token 数未超过预算，直接返回原消息
        if token_count <= self.token_budget:
            return messages

        # 需要压缩
        print(f"[MEMORY] Token 数 {token_count} 超过预算 {self.token_budget}，开始压缩...")

        # 保留第一条（system prompt）和最后 6 条消息
        if len(messages) <= 7:
            # 消息太少，不需要压缩
            return messages

        # 保留第一条（system）和最后 6 条消息
        preserved_messages = [messages[0]] + messages[-6:]

        # 取中间的旧消息（要被压缩的部分）
        old_messages = messages[1:-6]
        original_count = len(old_messages)

        # 生成摘要
        summary = await self._summarize(old_messages)

        # 用摘要替换旧消息
        summary_message = {
            "role": "system",
            "content": f"[历史摘要]: {summary}"
        }

        # 构建压缩后的消息列表
        compressed_messages = [messages[0]] + [summary_message] + messages[-6:]

        # 保存摘要到历史文件
        self._save_to_history(summary, original_count)

        print(f"[MEMORY] 已压缩 {original_count} 条消息")
        return compressed_messages

    async def _summarize(self, messages: List[Dict]) -> str:
        """
        生成消息摘要

        参数：
            messages: 要压缩的消息列表

        返回：
            str: 摘要文本
        """
        # 把消息拼接成文本
        messages_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            messages_text += f"{role}: {content}\n\n"

        # 构造摘要请求
        prompt = f"""请用 3-5 句话概括以下对话的关键信息，保留重要的事实和结论，省略过程细节和寒暄。只输出摘要，不要其他内容。

对话内容：
{messages_text}"""

        try:
            # 调用 LLM 生成摘要
            response = await self.provider.chat(
                messages=[{"role": "user", "content": prompt}],
                tools=[],
                model=""  # 使用默认模型
            )

            if response.content:
                return response.content.strip()
            else:
                return "（摘要生成失败，旧消息已丢弃）"
        except Exception as e:
            print(f"[MEMORY] 摘要生成失败: {e}")
            return "（摘要生成失败，旧消息已丢弃）"

    def _save_to_history(self, summary: str, original_count: int):
        """
        保存摘要到历史文件

        参数：
            summary: 摘要文本
            original_count: 被压缩的原始消息数量
        """
        history_path = os.path.join(self._memory_dir, "HISTORY.md")

        # 构造内容
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"## {current_time}\n压缩了 {original_count} 条旧消息\n\n{summary}\n\n---\n"

        # 追加写入文件
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(content)