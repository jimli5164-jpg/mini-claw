"""
ContextBuilder 上下文构建器模块

负责构建 AI Agent 的系统提示词和对话上下文，包含人设、记忆和工作区信息。
"""

import os
from datetime import datetime
from typing import List, Dict, Optional


class ContextBuilder:
    """
    上下文构建器类
    
    负责加载人设、记忆，并构建完整的系统提示词和对话消息列表。
    
    属性：
        workspace: 工作区路径
        identity_file: 人设文件名，默认为 identity.md
    """
    
    def __init__(self, workspace: str, identity_file: str = "identity.md", skills_summary: str = ""):
        """
        初始化上下文构建器
        
        参数：
            workspace: 工作区路径
            identity_file: 人设文件名，默认为 identity.md
            skills_summary: 技能摘要字符串，默认为空
        """
        self.workspace = os.path.abspath(workspace)
        self.identity_file = identity_file
        self.skills_summary = skills_summary
    
    def _load_identity(self) -> str:
        """
        加载人设文件内容
        
        读取工作区中的人设文件，如果文件不存在则返回默认人设内容。
        
        返回：
            str: 人设内容或默认人设
        """
        identity_path = os.path.join(self.workspace, self.identity_file)
        
        if os.path.exists(identity_path):
            try:
                with open(identity_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"读取人设文件失败: {str(e)}"
        else:
            # 返回默认人设
            return """你是一个专业的 AI 助手，擅长帮助用户解决各种问题。
你具备丰富的知识和良好的沟通能力，能够理解用户需求并提供有用的建议。
请用友好、专业的语言回答问题。"""
    
    def _load_memory(self) -> str:
        """
        加载长期记忆
        
        读取工作区 memory 目录中的 MEMORY.md 文件，为第六章预留的接口。
        
        返回：
            str: 记忆内容，文件不存在时返回空字符串
        """
        memory_path = os.path.join(self.workspace, "workspace", "memory", "MEMORY.md")
        
        if os.path.exists(memory_path):
            try:
                with open(memory_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"读取记忆文件失败: {str(e)}"
        else:
            return ""
    
    def build_system_prompt(self) -> str:
        """
        构建完整的 System Prompt
        
        拼接人设内容、当前时间、工作区路径和长期记忆，形成完整的系统提示词。
        
        返回：
            str: 完整的系统提示词
        """
        identity = self._load_identity()
        memory = self._load_memory()
        
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        
        # 构建系统提示词
        prompt_parts = [
            "# 角色定位",
            identity,
            "",
            "# 核心指令",
            "你拥有调用外部工具的能力。在回答用户问题时，请遵循以下策略：",
            "",
            "**工具使用指南：**",
            "- **web_search**: 搜索实时信息（天气、新闻、最新数据等）",
            "- **read_file**: 读取工作区内指定文件的内容",
            "- **write_file**: 将内容写入工作区内指定文件",
            "- **list_dir**: 列出工作区内指定目录的内容",
            "- **exec**: 在工作区内执行 shell 命令",
            "- **get_time**: 获取当前时间",
            "- **web_fetch**: 获取指定网页的内容",
            "",
            "**必须调用工具的情况：**",
            "1. 询问实时信息（如天气、新闻、股票）→ 使用 web_search",
            "2. 需要查看文件内容 → 使用 read_file",
            "3. 需要创建或修改文件 → 使用 write_file",
            "4. 需要了解目录结构 → 使用 list_dir",
            "",
            "**技能使用说明：**",
            "- 你可以使用 skills/ 目录下的技能，但不需要先读取 SKILL.md 文件",
            "- 技能只是告诉你如何完成任务的指南，实际执行时直接使用工具即可",
            "- 例如：查询天气时，直接使用 web_search 搜索，不需要先读取 weather/SKILL.md",
            "",
            "**工作流程：**",
            "1. 分析用户问题，确定需要什么工具",
            "2. 直接调用工具获取信息",
            "3. 根据工具返回结果，用自然语言总结回答用户",
            "",
            "**禁止行为：**",
            "- 不要编造信息，必须使用工具获取真实数据",
            "- 不要循环调用 list_dir 探索目录",
            "- 不要在没有明确需求的情况下读取技能文件",
            "",
            "**思考过程：**",
            "在调用工具之前，请先输出你的思考过程，格式如下：",
            "【思考】你的思考内容",
            "例如：【思考】用户想查询上海天气，需要使用 web_search 工具搜索实时天气信息",
            "",
            "# 当前时间",
            f"{current_time}",
            "",
            "# 工作区",
            f"工作区路径: {self.workspace}",
        ]

        # ★ 重要：长期记忆
        if memory:
            prompt_parts.append(f"\n\n## 长期记忆\n以下是你对用户的已有了解：\n{memory}")
        prompt_parts.append(self._memory_instructions())   # ★ 记忆更新指引

        result = "\n\n".join(prompt_parts)

        # 追加技能摘要
        if self.skills_summary:
            result += f"\n\n## 可用技能\n{self.skills_summary}"

        return result

    def _memory_instructions(self) -> str:
        return """
    \n\n## 记忆管理指引
    当你在对话中发现以下类型的重要信息时，使用 write_file 工具更新 工作目录下的workspace/memory/MEMORY.md：
    - 用户的姓名、职业、技术偏好
    - 用户的项目信息和工作习惯
    - 用户明确要求你记住的事情
    - 用户纠正过你的错误（避免下次再犯）

    更新时读取现有内容，在末尾追加新条目，保持 Markdown 列表格式。
    不要记录琐碎的对话细节，只记录长期有价值的信息。
    """

    
    def build_messages(self, history: Optional[List[Dict[str, str]]] = None, current_message: str = "") -> List[Dict[str, str]]:
        """
        构建完整的消息列表
        
        将系统提示词、历史对话和当前用户消息组合成完整的 messages 列表。
        
        参数：
            history: 历史对话列表，每个元素为 {"role": "...", "content": "..."} 格式
            current_message: 当前用户消息内容
            
        返回：
            list[dict]: 完整的消息列表，包含系统提示词、历史对话和当前消息
        """
        # 创建系统消息
        messages = [{
            "role": "system",
            "content": self.build_system_prompt()
        }]
        
        # 添加历史对话
        if history:
            messages.extend(history)
        
        # 添加当前用户消息（如果有）
        if current_message.strip():
            messages.append({
                "role": "user",
                "content": current_message
            })
        
        return messages
