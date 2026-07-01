"""飞书渠道实现模块（独立进程版本）。

使用独立进程运行飞书 WebSocket 长连接，避免与主进程事件循环冲突。
支持自动重连、心跳保持、优雅降级。
"""

import asyncio
import json
import multiprocessing
import queue
import re
import sys
import threading
import time
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequestBuilder,
    CreateMessageRequestBodyBuilder,
)

from bus.queue import InboundMessage, OutboundMessage, MessageBus
from channels.base import Channel


# ---------------------------------------------------------------------------
# 独立工作进程
# ---------------------------------------------------------------------------

_MAX_RECONNECT_DELAY = 60  # 最大重连间隔（秒）


def _feishu_worker(
    app_id: str,
    app_secret: str,
    verification_token: str,
    encrypt_key: str,
    out_queue: multiprocessing.Queue,
):
    """飞书 WebSocket 工作进程。

    在独立进程中运行，支持自动重连。所有接收到的消息通过
    ``out_queue`` 发送给主进程。
    """

    # 强制重定向 stdout，确保子进程输出可见
    sys.stdout.flush()

    print(
        "[FeishuWorker] 进程启动 (PID=%d)" % multiprocessing.current_process().pid
    )
    sys.stdout.flush()

    # ---- 消息回调 ----
    def on_message(data: Any) -> None:
        """飞书消息接收回调。"""
        try:
            event = data.event
            sender_id = event.sender.sender_id.open_id
            chat_id = event.message.chat_id
            message_type = event.message.message_type
            sender_type = event.sender.sender_type
            chat_type = getattr(event.message, "chat_type", "") or ""

            # 打印收到的原始事件摘要（调试用）
            print(
                "[FeishuWorker] 📩 收到事件: sender=%s..., chat_type=%s, msg_type=%s, sender_type=%s"
                % (sender_id[:16], chat_type, message_type, sender_type)
            )
            sys.stdout.flush()

            # 过滤机器人自己的消息
            if sender_type == "app":
                print("[FeishuWorker]   跳过：来自机器人自身")
                sys.stdout.flush()
                return

            # 目前只处理文本消息
            if message_type != "text":
                print(
                    "[FeishuWorker]   跳过：非文本消息 (%s)" % message_type
                )
                sys.stdout.flush()
                return

            content = json.loads(event.message.content)
            text = content.get("text", "")

            # 去掉 @ 提及，保留正文
            text = re.sub(r"@_all|@\S+", "", text).strip()
            if not text:
                print("[FeishuWorker]   跳过：空文本")
                sys.stdout.flush()
                return

            print(
                "[FeishuWorker] ✅ 投递消息: sender=%s..., chat_type=%s, text=%s"
                % (sender_id[:16], chat_type, text[:50])
            )
            sys.stdout.flush()

            message = {
                "channel": "feishu",
                "sender_id": sender_id,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "content": text,
            }
            out_queue.put(("inbound", message))
            print("[FeishuWorker]   已放入队列")
            sys.stdout.flush()

        except Exception as e:
            print(f"[FeishuWorker] ❌ 消息处理异常: {e}")
            import traceback

            traceback.print_exc()
            sys.stdout.flush()

    # ---- 主循环：创建连接 + 自动重连 ----
    reconnect_delay = 1

    while True:
        try:
            print("[FeishuWorker] 正在启动 WebSocket...")
            sys.stdout.flush()

            # 注意：WebSocket 模式下事件不需要加密/签名校验，
            # 连接本身已通过 app_id/app_secret 认证。传入空字符串禁用校验，
            # 否则 SDK 会比对签名失败后静默丢弃事件。
            # 如果确实需要事件加密，请在 config.json 中配置飞书后台的 encrypt_key。
            event_handler = (
                lark.EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(on_message)
                .build()
            )

            client = lark.ws.Client(
                app_id,
                app_secret,
                event_handler=event_handler,
                log_level=lark.LogLevel.DEBUG,  # DEBUG 级别便于诊断
            )

            print("[FeishuWorker] WebSocket 客户端已创建，开始连接...")
            print(
                "[FeishuWorker] 已注册事件: p2_im_message_receive_v1"
            )
            sys.stdout.flush()

            # 阻塞调用，直到 WebSocket 断开才返回
            client.start()
            print("[FeishuWorker] ⚠️ WebSocket 连接已断开")
            sys.stdout.flush()

        except Exception as e:
            print(f"[FeishuWorker] WebSocket 异常（将自动重连）: {e}")
            import traceback

            traceback.print_exc()
            sys.stdout.flush()

        # ---- 重连逻辑 ----
        print(
            "[FeishuWorker] %d 秒后重连..." % reconnect_delay
        )
        sys.stdout.flush()
        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, _MAX_RECONNECT_DELAY)


# ---------------------------------------------------------------------------
# 主进程渠道
# ---------------------------------------------------------------------------


class FeishuChannel(Channel):
    """飞书渠道，通过独立进程运行 WebSocket 长连接。"""

    def __init__(
        self,
        bus: MessageBus,
        app_id: str,
        app_secret: str,
        verification_token: str = "",
        encrypt_key: str = "",
    ):
        super().__init__("feishu", bus)
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key

        self._process: multiprocessing.Process | None = None
        self._out_queue: multiprocessing.Queue | None = None
        self._running = False

        # 飞书 API 客户端（复用，避免每次 send 都获取 token）
        self._api_client: lark.Client | None = None
        self._api_client_ts: float = 0

    # ---- 生命周期 ----

    async def start(self) -> None:
        """启动飞书 WebSocket 客户端（独立进程）。"""
        print("[FeishuChannel] start() 被调用")
        self._running = True

        # 主线程创建 API 客户端
        self._api_client = self._build_api_client()
        self._api_client_ts = time.time()
        print("[FeishuChannel] 飞书 API 客户端已创建")

        # 进程间通信队列
        self._out_queue = multiprocessing.Queue()

        # 启动桥接线程——在 start() 内部捕获当前事件循环引用，
        # 传给线程函数，因为线程内部无法通过 get_event_loop() 获取
        loop = asyncio.get_running_loop()

        self._bridge_thread = threading.Thread(
            target=self._run_bridge,
            args=(loop,),
            name="FeishuBridge",
            daemon=True,
        )
        self._bridge_thread.start()
        print("[FeishuChannel] 桥接线程已启动")

        # 创建并启动独立进程
        self._process = multiprocessing.Process(
            target=_feishu_worker,
            args=(
                self.app_id,
                self.app_secret,
                self.verification_token,
                self.encrypt_key,
                self._out_queue,
            ),
            daemon=True,
            name="FeishuWorker",
        )
        self._process.start()
        print(f"[FeishuChannel] 独立进程已启动, PID={self._process.pid}")

        # 后台任务
        asyncio.create_task(self._watch_worker())

    async def stop(self) -> None:
        """停止飞书渠道。"""
        print("[FeishuChannel] 停止渠道")
        self._running = False
        if self._process:
            self._process.terminate()
            self._process.join(timeout=5)
            if self._process.is_alive():
                self._process.kill()
            print("[FeishuChannel] 独立进程已终止")

    # ---- 桥接线程 ----

    def _run_bridge(self, loop: asyncio.AbstractEventLoop) -> None:
        """在独立线程中持续读取 multiprocessing.Queue，桥接到 asyncio。

        这是解决 macOS 死锁的关键：所有 multiprocessing.Queue 操作
        都在这个专用线程中进行，与事件循环线程完全隔离。

        参数：
            loop: 主线程的事件循环引用（线程内无法通过 get_event_loop 获取）
        """
        print("[FeishuBridge] 桥接线程启动")

        while self._running:
            try:
                # 仅在此线程中阻塞等待 multiprocessing 消息
                msg = self._out_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[FeishuBridge] 队列读取异常: {e}")
                time.sleep(0.5)
                continue

            # 防御性检查
            if not msg or len(msg) != 2:
                print(f"[FeishuBridge] ⚠️ 异常格式消息: {msg}")
                continue

            msg_type, data = msg
            print(f"[FeishuBridge] 📥 收到消息: type={msg_type}")

            if msg_type == "inbound":
                # 通过线程安全的方式投递到事件循环
                future = asyncio.run_coroutine_threadsafe(
                    self._handle_inbound(data), loop
                )
                future.add_done_callback(self._on_inbound_done)

        print("[FeishuBridge] 桥接线程结束")
        
    def _on_inbound_done(self, future):
        try:
            future.result()
        except Exception as e:
            print(f"[FeishuBridge] ❌ _handle_inbound 异常: {e}")
            import traceback
            traceback.print_exc()


    async def _handle_inbound(self, data: dict) -> None:
        """在事件循环中处理入站消息（由桥接线程触发）。"""
        try:
            message = InboundMessage(
                channel=data["channel"],
                sender_id=data.get("sender_id", ""),
                chat_id=data.get("chat_id", ""),
                content=data["content"],
                chat_type=data.get("chat_type", ""),
            )
            await self.bus.publish_inbound(message)
            print(
                "[FeishuChannel] ✅ 入站消息已发布,"
                " 队列大小=%d" % self.bus.inbound_queue.qsize()
            )
        except Exception as e:
            print(f"[FeishuChannel] ❌ 消息发布失败: {e}")
            import traceback
            traceback.print_exc()

    # ---- Worker 存活检测 ----

    async def _watch_worker(self) -> None:
        """监控子进程，死亡后自动重启。"""
        print("[FeishuChannel] Worker 存活检测启动")
        while self._running:
            await asyncio.sleep(5)
            if self._process is None:
                continue
            if not self._process.is_alive():
                exit_code = self._process.exitcode
                print(
                    "[FeishuChannel] ⚠️ Worker 已死亡 (exitcode=%s), 正在重启..."
                    % exit_code
                )
                try:
                    self._process = multiprocessing.Process(
                        target=_feishu_worker,
                        args=(
                            self.app_id,
                            self.app_secret,
                            self.verification_token,
                            self.encrypt_key,
                            self._out_queue,
                        ),
                        daemon=True,
                        name="FeishuWorker",
                    )
                    self._process.start()
                    print(
                        "[FeishuChannel] Worker 已重启, PID=%d"
                        % self._process.pid
                    )
                except Exception as e:
                    print(f"[FeishuChannel] Worker 重启失败: {e}")
        print("[FeishuChannel] Worker 存活检测结束")

    # ---- 发送回复 ----

    def _build_api_client(self) -> lark.Client:
        """构建飞书 API 客户端（同步方法，必须在主线程调用）。"""
        return (
            lark.Client.builder()
            .app_id(self.app_id)
            .app_secret(self.app_secret)
            .log_level(lark.LogLevel.WARNING)
            .build()
        )

    async def _ensure_api_client(self) -> None:
        """确保 API 客户端 token 在有效期内。

        tenant_access_token 有效期 2 小时，提前 5 分钟刷新。
        """
        TOKEN_TTL = 2 * 3600
        REFRESH_BEFORE = 5 * 60
        now = time.time()
        if self._api_client is not None and (
            now - self._api_client_ts < TOKEN_TTL - REFRESH_BEFORE
        ):
            return
        self._api_client = self._build_api_client()
        self._api_client_ts = time.time()
        print("[FeishuChannel] 飞书 API 客户端已刷新")

    async def send(self, message: OutboundMessage) -> None:
        """发送回复消息到飞书。

        - P2P 私聊：优先使用 open_id，备选 chat_id
        - 群聊：使用 chat_id
        - 未知类型：先试 chat_id，失败回退 open_id
        """
        chat_id = message.chat_id
        sender_id = message.sender_id or ""
        chat_type = message.chat_type or ""

        print(
            "[FeishuChannel] 📤 发送消息: chat_id=%s, chat_type=%s, sender_id=%s"
            % (chat_id, chat_type, sender_id[:16] if sender_id else "无")
        )

        content_json = json.dumps({"text": message.content}, ensure_ascii=False)

        # 构造发送策略列表
        if chat_type == "p2p" and sender_id:
            strategies = [
                ("open_id", sender_id, "P2P open_id"),
                ("chat_id", chat_id, "P2P chat_id (fallback)"),
            ]
        elif chat_type == "group":
            strategies = [("chat_id", chat_id, "群聊 chat_id")]
        else:
            strategies = [("chat_id", chat_id, "默认 chat_id")]
            if sender_id:
                strategies.append(
                    ("open_id", sender_id, "默认 open_id (fallback)")
                )

        await self._ensure_api_client()
        loop = asyncio.get_running_loop()
        last_error = None

        for receive_id_type, receive_id, label in strategies:
            if not receive_id:
                continue
            try:
                print(
                    "[FeishuChannel]   尝试策略: %s (%s=%s)"
                    % (label, receive_id_type, receive_id[:24])
                )

                response = await loop.run_in_executor(
                    None,
                    lambda rid=receive_id, rit=receive_id_type: (
                        self._api_client.im.v1.message.create(
                            CreateMessageRequestBuilder()
                            .receive_id_type(rit)
                            .request_body(
                                CreateMessageRequestBodyBuilder()
                                .receive_id(rid)
                                .msg_type("text")
                                .content(content_json)
                                .build()
                            )
                            .build()
                        )
                    ),
                )

                code = getattr(response, "code", -1)
                msg_str = getattr(response, "msg", "")
                if code != 0:
                    last_error = "API code=%s msg=%s" % (code, msg_str)
                    print("[FeishuChannel]   ❌ %s" % last_error)
                    continue  # 尝试下一个策略

                print(
                    "[FeishuChannel]   ✅ 发送成功 (%s): code=%s"
                    % (label, code)
                )
                return

            except Exception as e:
                last_error = str(e)
                print("[FeishuChannel]   ❌ 策略 %s 异常: %s" % (label, last_error))
                continue

        print(
            "[FeishuChannel] ❌ 所有策略均失败! 最后错误: %s" % last_error
        )
        import traceback

        traceback.print_exc()
