"""实时推送（SSE）：把违规 / 预警 / 摄像头状态事件推给前端

用法（前端）：
  const es = new EventSource(`/api/realtime/stream?token=${token}`);
  es.addEventListener("violation", e => ...);
  es.addEventListener("warning", e => ...);
  es.addEventListener("camera_status", e => ...);

SSE 事件是一行 `event: <type>` + `data: <json>`，每 15s 发一次注释心跳保活。
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..security import decode_token
from ..services.events import bus

router = APIRouter()


@router.get("/stream")
async def stream(request: Request, token: str = Query(...)):
    """SSE 长连接（EventSource 无法设置 Authorization 头，故 token 走 query）。"""
    try:
        decode_token(token)
    except Exception:  # noqa: BLE001 - JWT 各类异常统一按未授权处理
        raise HTTPException(status_code=401, detail="认证失败，请重新登录")

    queue = bus.subscribe()

    async def event_generator():
        try:
            # 告诉浏览器断线后 3s 重连
            yield "retry: 3000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield (
                    f"event: {payload['type']}\n"
                    f"data: {json.dumps(payload['data'], ensure_ascii=False)}\n\n"
                )
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
