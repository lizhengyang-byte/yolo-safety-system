"""FastAPI 应用入口"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import auth, cameras, demo, logs, violations

# 建表（生产环境建议用 init.sql 或 alembic 迁移）
Base.metadata.create_all(bind=engine)

# 确保图片存储目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="工地AI安全智能监测系统",
    description="基于YOLO的安全帽/马甲/口罩违规识别 + 后台管理系统",
    version="1.0.0",
)

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


@app.get("/api/health", tags=["健康检查"])
def health():
    return {"status": "ok", "service": "yolo-safety-backend"}
