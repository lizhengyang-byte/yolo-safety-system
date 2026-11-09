"""FastAPI 应用入口"""
import asyncio
import os
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import (
    auth,
    cameras,
    demo,
    logs,
    realtime,
    violations,
    warnings,
)
from .routers import settings as settings_router

# 建表（生产环境建议用 init.sql 或 alembic 迁移）
Base.metadata.create_all(bind=engine)


def _ensure_schema():
    """轻量 schema 演进：为已存在的 violations 表补齐新增列（SQLite/MySQL 通用）。

    新列：anno_url（标注证据图）、detections_json（帧内检测目标明细）。
    create_all 不会修改已存在的表，这里手动 ALTER TABLE 补列。
    """
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(engine)
        if "violations" not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns("violations")}
        for col, ddl in {"anno_url": "VARCHAR(512)", "detections_json": "TEXT"}.items():
            if col not in existing:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE violations ADD COLUMN {col} {ddl}"))
                print(f"[startup] 已为 violations 表补充列 {col}")
    except Exception as e:
        print(f"[startup] schema 检查跳过（不影响启动）: {e}")


_ensure_schema()

# 确保图片存储目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="工地AI安全智能监测系统",
    description="基于YOLO的安全帽/马甲/口罩违规识别 + 后台管理系统",
    version="1.0.0",
)


def _warmup_demo_model():
    """后台线程预热演示模型：避免首次 /api/demo/detect 请求加载模型卡顿 10~30s"""
    try:
        from .routers import demo

        demo.get_detector()
        print("[startup] 演示模型（ppe.pt）预热完成")
    except Exception as e:
        print(f"[startup] 演示模型预热失败（首次请求时会再尝试加载）: {e}")


@app.on_event("startup")
async def startup_warmup():
    # 绑定事件循环给 SSE 事件总线（支持从同步线程安全推送）
    from .services.events import bus
    from .services.report_scheduler import start_report_scheduler

    bus.bind_loop(asyncio.get_running_loop())
    start_report_scheduler()
    threading.Thread(target=_warmup_demo_model, daemon=True).start()

# CORS：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载抓拍图片静态目录，前端直接访问 image_url
app.mount(
    "/images",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="images",
)

# 业务路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["摄像头"])
app.include_router(violations.router, prefix="/api/violations", tags=["违规记录"])
app.include_router(logs.router, prefix="/api/logs", tags=["安全日志"])
app.include_router(demo.router, prefix="/api/demo", tags=["临时演示"])
app.include_router(warnings.router, prefix="/api/warnings", tags=["预警中心"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["实时推送"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["系统配置"])


@app.get("/api/health", tags=["健康检查"])
def health():
    return {"status": "ok", "service": "yolo-safety-backend"}
