"""进程内实时事件总线（供 SSE 推送使用）

说明：
- 单 uvicorn worker 下用内存队列即可；多 worker 部署需替换为 Redis Pub/Sub，
  否则只有处理请求的那个 worker 能推送到自己的订阅者。
- publish() 可在同步线程（如线程池里的接口）调用，内部通过 call_soon_threadsafe
  切回事件循环派发。
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict]:
        q: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict]) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, event: str, data: Any) -> None:
        """广播一条事件（线程安全）。"""
        payload = {
            "type": event,
            "data": data,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        with self._lock:
            loop = self._loop
            subscribers = list(self._subscribers)
        if loop is None or not loop.is_running():
            return

        def _dispatch() -> None:
            for q in subscribers:
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

        try:
            loop.call_soon_threadsafe(_dispatch)
        except RuntimeError:
            pass


bus = EventBus()
