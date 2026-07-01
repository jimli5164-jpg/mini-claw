"""
OpenAI 兼容提供者模块

实现与 OpenAI API 兼容的 LLM 提供者，支持硅基流动等兼容服务。
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到 Python 模块搜索路径
_root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root_dir))

import aiohttp

from agent.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class OpenAICompatProvider(LLMProvider):
    """
    OpenAI 兼容的 LLM 提供者
    
    支持与 OpenAI API 格式兼容的服务，如硅基流动。
    """
    
    def __init__(self, api_key: str, base_url: str, model: str):
        """
        初始化 OpenAI 兼容提供者
        
        参数：
            api_key: API 密钥
            base_url: API 基础地址
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        异步发送聊天消息
        
        参数：
            messages: 消息列表
            tools: 工具定义列表
            model: 模型名称（可选，覆盖默认模型）
        
        返回：
            LLMResponse: LLM 响应对象
        """
        url = f"{self.base_url}/chat/completions"
        
        # 构建请求体，仅当 tools 非空时才传递 tools 和 tool_choice
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120)
            ) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                # 尝试解析 JSON 响应
                try:
                    response_data = await response.json()
                except Exception as json_error:
                    try:
                        text_response = await response.text()
                        return LLMResponse(
                            content=f"API 响应格式错误: {str(json_error)}. 响应内容: {text_response[:200]}",
                            finish_reason="error"
                        )
                    except Exception as text_error:
                        return LLMResponse(
                            content=f"API 响应读取失败: {str(json_error)}, {str(text_error)}",
                            finish_reason="error"
                        )
                
                # 检查响应是否为字典
                if not isinstance(response_data, dict):
                    return LLMResponse(
                        content=f"API 响应不是预期的 JSON 对象: {str(response_data)[:200]}",
                        finish_reason="error"
                    )
                
                if response.status != 200:
                    # 兼容多种错误响应格式
                    # 格式1: {"error": {"message": "..."}} - OpenAI 标准格式
                    # 格式2: {"code": "...", "message": "..."} - 硅基流动格式
                    # 格式3: {"error": "直接的错误消息"} - 简单格式
                    error_val = response_data.get("error")
                    if error_val:
                        if isinstance(error_val, dict):
                            error_msg = error_val.get("message", json.dumps(error_val))
                        elif isinstance(error_val, str):
                            error_msg = error_val
                        else:
                            error_msg = json.dumps(error_val)
                    elif "message" in response_data:
                        # 硅基流动格式: {"code": "...", "message": "..."}
                        error_msg = response_data.get("message", json.dumps(response_data))
                    else:
                        error_msg = json.dumps(response_data)
                    
                    return LLMResponse(
                        content=f"API 调用失败: {error_msg}",
                        finish_reason="error"
                    )
                
                # 解析响应
                choices = response_data.get("choices", [])
                if not choices:
                    return LLMResponse(
                        content=f"未收到响应。响应内容: {json.dumps(response_data, ensure_ascii=False)[:200]}",
                        finish_reason="error"
                    )
                
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content")
                
                # 解析工具调用
                tool_calls = []
                if "tool_calls" in message and message["tool_calls"]:
                    for tool_call in message["tool_calls"]:
                        tool_calls.append(ToolCallRequest(
                            id=tool_call.get("id", ""),
                            name=tool_call.get("function", {}).get("name", ""),
                            arguments=json.loads(tool_call.get("function", {}).get("arguments", "{}")),
                            reasoning_content=None  # 部分模型支持，需要额外解析
                        ))
                
                # 解析使用统计
                usage = response_data.get("usage", {})
                
                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage=usage
                )
