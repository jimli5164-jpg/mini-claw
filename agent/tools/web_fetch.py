"""
网页抓取工具模块

使用 httpx 抓取网页内容，并用 html2text 转换为纯文本。
"""

import asyncio
import re
from typing import Dict, Any
from urllib.parse import urlparse

from agent.tools.base import Tool


class WebFetchTool(Tool):
    """
    网页抓取工具

    抓取指定 URL 的网页内容，转换成纯文本返回。

    属性：
        name: 工具名称
        description: 工具功能描述
        parameters: 工具参数定义
    """

    @property
    def name(self) -> str:
        """工具名称"""
        return "web_fetch"

    @property
    def description(self) -> str:
        """工具功能描述"""
        return (
            "抓取指定 URL 的网页内容。当你需要阅读某个具体网页的详细内容时使用。"
            "通常配合 web_search 工具先搜索再抓取。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """工具参数定义"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的网页 URL"
                }
            },
            "required": ["url"]
        }

    async def execute(self, **kwargs) -> str:
        """
        执行网页抓取

        参数：
            url: 要抓取的网页 URL

        返回：
            str: 网页内容（Markdown 格式）
        """
        url = kwargs.get("url", "")

        # 步骤 1：URL 安全检查
        if not url:
            return "错误：URL 不能为空"

        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                return "安全拦截：URL 缺少协议（需要 http:// 或 https://）"
            if parsed.scheme.lower() not in ("http", "https"):
                return "安全拦截：只允许 http/https 协议"
            if not parsed.netloc:
                return "错误：URL 格式不正确"
        except Exception as e:
            return f"错误：URL 解析失败 - {str(e)}"

        try:
            # 步骤 2：发送 HTTP GET 请求
            import httpx

            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=True,
                headers={"User-Agent": user_agent}
            ) as client:
                response = await client.get(url)

                if response.status_code // 100 != 2:
                    return f"抓取失败：HTTP {response.status_code}"

                # 步骤 3：HTML 转换成纯文本
                import html2text

                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0

                text = h.handle(response.text)

                # 步骤 4：清理输出
                # 去除连续多个空行
                text = re.sub(r"\n{3,}", "\n\n", text)

                # 截断超长输出
                max_length = 12000
                if len(text) > max_length:
                    text = text[:max_length] + "\n...(内容过长，已截断)"

                return text

        except ImportError as e:
            missing_lib = str(e).split()[-1]
            return f"错误：请先安装依赖库 (pip install httpx html2text)"
        except httpx.TimeoutException:
            return "错误：请求超时（15秒）"
        except httpx.ConnectError:
            return "错误：网络连接失败，请检查网络或 URL 是否正确"
        except httpx.DNSLookupError:
            return "错误：DNS 解析失败，请检查域名是否正确"
        except Exception as e:
            return f"抓取失败：{type(e).__name__} - {str(e)}"
