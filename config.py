"""
配置模块

负责加载和管理 MiniClaw 的配置参数。
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MiniClawConfig:
    """
    MiniClaw 配置数据类
    
    封装所有配置参数，包括 API 密钥、模型设置、工作区路径等。
    
    字段：
        api_key: 硅基流动 API 密钥
        base_url: API 服务地址，默认为硅基流动
        model: 使用的模型名称
        workspace: 工作区路径，默认为当前目录
        max_iterations: 最大迭代次数，防止无限循环
        identity_file: 人设文件名
        bocha_api_key: 博查搜索 API 密钥
    """
    api_key: str = "sk-ehahfxrymyojqjenpitmsprwkukpyfzbcyijgfwmaapbzcni"
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Pro/moonshotai/Kimi-K2.5"
    workspace: str = "."
    max_iterations: int = 32
    identity_file: str = "identity.md"
    bocha_api_key: str = ""
    # 飞书配置
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""


def load_config(config_path: str = "config.json") -> MiniClawConfig:
    """
    加载配置文件
    
    从指定路径读取 JSON 配置文件，并支持环境变量覆盖。
    环境变量 MINICLAW_API_KEY 的优先级最高。
    
    参数：
        config_path: 配置文件路径，默认为 config.json
    
    返回：
        MiniClawConfig: 配置对象
    """
    config = MiniClawConfig()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if isinstance(config_data, dict):
                    if "api_key" in config_data:
                        config.api_key = config_data["api_key"]
                    if "base_url" in config_data:
                        config.base_url = config_data["base_url"]
                    if "model" in config_data:
                        config.model = config_data["model"]
                    if "workspace" in config_data:
                        config.workspace = config_data["workspace"]
                    if "max_iterations" in config_data:
                        config.max_iterations = config_data["max_iterations"]
                    if "identity_file" in config_data:
                        config.identity_file = config_data["identity_file"]
                    if "bocha_api_key" in config_data:
                        config.bocha_api_key = config_data["bocha_api_key"]
                    if "feishu" in config_data:
                        if "app_id" in config_data["feishu"]:
                            config.feishu_app_id = config_data["feishu"]["app_id"]
                        if "app_secret" in config_data["feishu"]:
                            config.feishu_app_secret = config_data["feishu"]["app_secret"]
                        if "verification_token" in config_data["feishu"]:
                            config.feishu_verification_token = config_data["feishu"]["verification_token"]
                        if "encrypt_key" in config_data["feishu"]:
                            config.feishu_encrypt_key = config_data["feishu"]["encrypt_key"]
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    # 环境变量优先级最高
    env_api_key = os.environ.get("MINICLAW_API_KEY")
    if env_api_key:
        config.api_key = env_api_key
    
    # 博查 API 密钥环境变量
    env_bocha_key = os.environ.get("BOCHA_API_KEY")
    if env_bocha_key:
        config.bocha_api_key = env_bocha_key
    
    return config
