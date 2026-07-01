"""
网络搜索工具模块

使用 DuckDuckGo 搜索互联网，获取最新信息。
"""

import asyncio
from typing import Dict, Any

from agent.tools.base import Tool


class WebSearchTool(Tool):
    """
    网络搜索工具

    使用 DuckDuckGo 搜索互联网，返回搜索结果。

    属性：
        name: 工具名称
        description: 工具功能描述
        parameters: 工具参数定义
    """

    @property
    def name(self) -> str:
        """工具名称"""
        return "web_search"

    @property
    def description(self) -> str:
        """工具功能描述"""
        return (
            "搜索互联网获取最新信息。当你需要查询实时信息、最新新闻或不确定的知识时使用。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """工具参数定义"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回几条结果",
                    "default": 5
                }
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> str:
        """
        执行网络搜索

        参数：
            query: 搜索关键词
            max_results: 最多返回结果数，默认 5

        返回：
            str: 搜索结果列表
        """
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)

        if not query:
            return "搜索出错: 搜索关键词不能为空"

        try:
            from ddgs import DDGS

            # 使用 asyncio.to_thread 包装同步方法
            def do_search():
                with DDGS() as ddgs:
                    results = ddgs.text(query, max_results=max_results)
                    return results

            search_results = await asyncio.to_thread(do_search)

            # 如果没有搜索结果
            if not search_results:
                return "未找到相关结果"

            # 格式化搜索结果
            output_parts = []
            for idx, result in enumerate(search_results, 1):
                title = result.get("title", "")
                href = result.get("href", "")
                body = result.get("body", "")
                output_parts.append(f"### {idx}. {title}\n链接: {href}\n{body}\n")

            result_text = "\n".join(output_parts)

            # 截断超长输出（超过 8000 字符）
            if len(result_text) > 8000:
                result_text = result_text[:8000] + "\n...(输出过长，已截断)"

            return result_text

        except ImportError:
            return "搜索出错: 请先安装 ddgs 库 (pip install ddgs)"
        except Exception as e:
            return f"搜索出错: {str(e)}"