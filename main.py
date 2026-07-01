#!/usr/bin/env python3
"""
MiniClaw - AI Agent 入口文件

基于 LLM 的智能代理系统，支持工具调用和对话管理。
"""

import asyncio
import sys
import os

# 将项目根目录添加到 Python 模块搜索路径
_root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root_dir)

from config import load_config
from agent.providers.openai_compat import OpenAICompatProvider
from agent.tools.registry import ToolRegistry
from agent.tools.filesystem import ReadFileTool, WriteFileTool, ListDirTool
from agent.tools.time import GetTimeTool
from agent.tools.shell import ExecTool
from agent.tools.web_search import WebSearchTool
from agent.tools.web_fetch import WebFetchTool
from agent.context import ContextBuilder
from agent.loop import AgentLoop
from agent.skills import SkillsLoader
from agent.session.manager import SessionManager
from bus.queue import MessageBus
from channels import CLIChannel
from gateway import Gateway


def build_agent() -> AgentLoop:
    """
    构建 Agent 实例
    
    加载配置、创建组件、注册工具，最后组装成完整的 AgentLoop。
    
    返回：
        AgentLoop: 完整配置的 Agent 循环实例
    """
    # 加载配置
    config = load_config()
    
    # 检查 API Key
    if not config.api_key:
        print("错误：API Key 为空，请在 config.json 中配置 api_key")
        sys.exit(1)
    
    # 创建 LLM 提供者
    provider = OpenAICompatProvider(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model
    )
    
    # 创建工具注册表并注册工具
    tool_registry = ToolRegistry()
    tool_registry.register(ReadFileTool(config.workspace))
    tool_registry.register(WriteFileTool(config.workspace))
    tool_registry.register(ListDirTool(config.workspace))
    tool_registry.register(GetTimeTool())
    tool_registry.register(ExecTool(config.workspace))
    tool_registry.register(WebSearchTool())
    tool_registry.register(WebFetchTool())
    
    # 加载技能系统
    skills_loader = SkillsLoader(os.path.join(config.workspace, "skills"))
    skills_summary = skills_loader.build_skills_summary()
    
    # 如果发现技能，打印技能数量
    if skills_summary:
        skills_count = len(skills_loader.list_skills())
        print(f"已发现 {skills_count} 个技能")
    
    # 创建上下文构建器
    context_builder = ContextBuilder(
        workspace=config.workspace,
        identity_file=config.identity_file,
        skills_summary=skills_summary
    )
    
    # 组装 AgentLoop
    agent = AgentLoop(
        provider=provider,
        tool_registry=tool_registry,
        context_builder=context_builder,
        model=config.model,
        max_iterations=config.max_iterations
    )
    
    # 打印已注册的工具列表
    print("已注册工具：")
    for tool_name in tool_registry.list_tools():
        print(f"  - {tool_name}")
    
    return agent


async def interactive_loop(agent: AgentLoop, session_manager: SessionManager, session_key: str = "cli:default"):
    """
    交互式对话循环
    
    处理用户输入，支持命令和正常对话，集成会话持久化。
    
    参数：
        agent: AgentLoop 实例
        session_manager: SessionManager 实例
        session_key: 会话键
    """
    print("\n进入交互式对话模式（输入 /exit 退出）")
    
    # 加载会话历史
    history = session_manager.get_history(session_key)
    if history:
        agent.history = history
        print(f"已加载 {len(history)} 条历史消息")
    
    while True:
        try:
            user_input = input(">>> ").strip()
            
            if user_input == "/exit":
                print("退出对话")
                break
            elif user_input == "/clear":
                agent.clear_history()
                session_manager.clear(session_key)
                print("历史记录已清空")
                continue
            elif user_input == "/tools":
                print("可用工具：")
                for tool_name in agent.get_tool_list():
                    print(f"  - {tool_name}")
                continue
            elif not user_input:
                continue
            
            # 执行 Agent（agent.run() 内部会更新 agent.history）
            print("\n" + "="*50)
            print("执行中...")
            print("-"*50)
            response = await agent.run(user_input)
            print("-"*50)
            print(f"💡 回答：{response}\n")
            
            # 同步历史到会话管理器
            session_manager.clear(session_key)
            for msg in agent.history:
                if msg.get("role") in ["user", "assistant"]:
                    session_manager.save_message(session_key, msg)
            
        except KeyboardInterrupt:
            print("\n用户中断，退出对话")
            break
        except Exception as e:
            print(f"发生错误：{e}")


def build_agent_factory(config) -> callable:
    """
    构建 Agent 工厂函数
    
    参数：
        config: 配置对象
    
    返回：
        callable: Agent 工厂函数（输入 session_key，返回 AgentLoop 实例）
    """
    # 创建 LLM 提供者（只创建一次，共享使用）
    provider = OpenAICompatProvider(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model
    )
    
    # 加载技能系统
    skills_loader = SkillsLoader(os.path.join(config.workspace, "skills"))
    skills_summary = skills_loader.build_skills_summary()
    
    # 如果发现技能，打印技能数量
    if skills_summary:
        skills_count = len(skills_loader.list_skills())
        print(f"已发现 {skills_count} 个技能")
    
    def agent_factory(session_key: str) -> AgentLoop:
        """
        Agent 工厂函数
        
        参数：
            session_key: 会话键
        
        返回：
            AgentLoop: Agent 实例
        """
        # 创建工具注册表（每个 Agent 独立创建）
        tool_registry = ToolRegistry()
        tool_registry.register(ReadFileTool(config.workspace))
        tool_registry.register(WriteFileTool(config.workspace))
        tool_registry.register(ListDirTool(config.workspace))
        tool_registry.register(GetTimeTool())
        tool_registry.register(ExecTool(config.workspace))
        tool_registry.register(WebSearchTool())
        tool_registry.register(WebFetchTool())
        
        # 创建上下文构建器（每个 Agent 独立创建）
        context_builder = ContextBuilder(
            workspace=config.workspace,
            identity_file=config.identity_file,
            skills_summary=skills_summary
        )
        
        # 创建会话管理器（每个会话独立）
        session_manager = SessionManager(os.path.join(config.workspace, "sessions"))
        
        # 加载历史消息
        history = session_manager.get_history(session_key)
        
        # 创建 AgentLoop
        agent = AgentLoop(
            provider=provider,
            tool_registry=tool_registry,
            context_builder=context_builder,
            model=config.model,
            max_iterations=config.max_iterations
        )
        
        # 设置历史消息
        if history:
            agent.history = history
        
        return agent
    
    return agent_factory


async def run_with_gateway():
    """
    使用网关模式运行
    
    创建消息总线、渠道和网关，启动异步消息循环。
    """
    config = load_config()
    
    # 检查 API Key
    if not config.api_key:
        print("错误：API Key 为空，请在 config.json 中配置 api_key")
        sys.exit(1)
    
    # 1. 创建 MessageBus
    bus = MessageBus()
    print("已创建消息总线")
    
    # 创建工具注册表（用于 CLI 渠道显示工具列表）
    tool_registry = ToolRegistry()
    tool_registry.register(ReadFileTool(config.workspace))
    tool_registry.register(WriteFileTool(config.workspace))
    tool_registry.register(ListDirTool(config.workspace))
    tool_registry.register(GetTimeTool())
    tool_registry.register(ExecTool(config.workspace))
    tool_registry.register(WebSearchTool())
    tool_registry.register(WebFetchTool())
    
    # 打印已注册的工具列表
    print("已注册工具：")
    tool_names = tool_registry.list_tools()
    for tool_name in tool_names:
        print(f"  - {tool_name}")
    
    # 2. 定义 agent_factory 工厂函数
    agent_factory = build_agent_factory(config)
    
    # 3. 注册渠道列表
    channels = []
    
    # CLI 渠道
    cli_channel = CLIChannel(bus)
    cli_channel.tool_names = tool_names
    channels.append(cli_channel)
    print("[启动] 已启用 CLI 渠道")

    # 飞书渠道（如果配置了 feishu app_id / app_secret 就自动启用）
    feishu_app_id = getattr(config, 'feishu_app_id', '') or ''
    feishu_app_secret = getattr(config, 'feishu_app_secret', '') or ''
    feishu_verification_token = getattr(config, 'feishu_verification_token', '') or ''
    feishu_encrypt_key = getattr(config, 'feishu_encrypt_key', '') or ''

    if feishu_app_id and feishu_app_secret:
        try:
            from channels.feishu import FeishuChannel
            feishu_channel = FeishuChannel(
                bus, feishu_app_id, feishu_app_secret,
                verification_token=feishu_verification_token,
                encrypt_key=feishu_encrypt_key
            )
            channels.append(feishu_channel)
            print("[启动] 已启用飞书渠道")
        except Exception as e:
            print(f"[启动] 飞书渠道初始化失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[启动] 未配置飞书（或配置不完整），跳过飞书渠道")
        if not feishu_app_id:
            print("    - feishu.app_id 为空")
        if not feishu_app_secret:
            print("    - feishu.app_secret 为空")
    
    # 4. 创建 Gateway
    gateway = Gateway(
        bus=bus,
        channels=channels,
        agent_factory=agent_factory
    )
    
    print("\n系统已启动，等待消息...")
    
    try:
        await gateway.run()
        
    except KeyboardInterrupt:
        print("\n[MiniClaw] 正在退出...")
        await gateway.shutdown()
        import os
        os._exit(0)


def main():
    """
    主入口函数
    
    打印启动 banner，构建 Agent，启动交互式循环。
    """
    banner = """
═══════════════════════════════════════════════════════════════
                    MiniClaw AI Agent
═══════════════════════════════════════════════════════════════
    基于 LLM 的智能代理系统，支持工具调用和对话管理
═══════════════════════════════════════════════════════════════
"""
    print(banner)
    
    try:
        config = load_config()
        
        # 使用网关模式运行（新架构）
        asyncio.run(run_with_gateway())
        
    except SystemExit:
        pass
    except Exception as e:
        print(f"启动失败：{e}")


if __name__ == "__main__":
    main()
