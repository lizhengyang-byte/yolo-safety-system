#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工地AI安全智能监测系统 - 前端演示快速启动（仅前端，不启动后端）
=====================================================
只启动前端 Vite 开发服务器并自动打开「临时演示」页面，适合快速演示 UI。

注意：
  - 本脚本**不会**启动后端 FastAPI。
  - 演示页的 AI 检测走 `/api/demo/detect`，登录也依赖后端 JWT，
    若后端未运行，页面会请求失败（提示 503 / 401）。
    请确认后端已在 8000 端口运行，或另开终端执行 `python start-local.py`。

用法（在仓库根目录执行）：
  python start-demo.py                # 仅启动前端并打开演示页
  python start-demo.py --no-browser   # 不自动打开浏览器
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"

FRONTEND_PORT = 3000
BACKEND_PORT = 8000
BACKEND_HOST = "127.0.0.1"

COLORS = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "cyan": "\033[96m", "reset": "\033[0m"}


def log(msg: str, color: str = "green", prefix: str = "[演示]") -> None:
    print(f"{COLORS.get(color, '')}{prefix} {msg}{COLORS['reset']}")
    sys.stdout.flush()


def setup_console() -> None:
    if os.name == "nt":
        try:
            subprocess.call("chcp 65001 >nul", shell=True)
        except OSError:
            pass
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                try:
                    reconfigure(encoding="utf-8", errors="replace")
                except (ValueError, OSError):
                    pass


def find_npm() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def open_browser(url: str) -> None:
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception as exc:  # noqa: BLE001
        log(f"自动打开浏览器失败（{exc}），请手动访问 {url}", color="yellow")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="工地AI安全智能监测系统 - 前端演示快速启动（仅前端，不启动后端）")
    parser.add_argument("--no-browser", action="store_true",
                        help="启动后不自动打开浏览器")
    parser.add_argument("--timeout", type=float, default=90.0,
                        help="等待前端就绪的超时秒数（默认 90）")
    args = parser.parse_args()

    setup_console()

    log("=" * 60)
    log("前端演示快速启动（仅前端，不启动后端）", color="cyan")
    log("=" * 60)

    if not FRONTEND_DIR.exists():
        log(f"找不到 frontend 目录：{FRONTEND_DIR}", color="red")
        return 1
    if not (FRONTEND_DIR / "node_modules").exists():
        log("⚠️  frontend/node_modules 未安装，请先执行 npm install", color="red")
        return 1

    # 后端健康提示：演示 AI 检测与登录都依赖后端
    if not port_open(BACKEND_PORT, BACKEND_HOST):
        log("⚠️  检测到后端未在 8000 端口运行（未启动或已关闭）。", color="yellow")
        log("    演示页的 AI 检测（/api/demo/detect）与登录将不可用。", color="yellow")
        log("    另开终端执行 `python start-local.py` 可一并启动后端。", color="yellow")
    else:
        log("✅ 已检测到后端运行中（8000），演示 AI 检测可用。", color="green")

    if port_open(FRONTEND_PORT):
        log(f"端口 {FRONTEND_PORT} 已被占用，前端可能已在运行。", color="yellow")
    else:
        log(f"启动前端 Vite（http://localhost:{FRONTEND_PORT}）...")
        proc = subprocess.Popen(
            [find_npm(), "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        def pump() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(f"{COLORS['cyan']}[frontend] {line}{COLORS['reset']}")
                sys.stdout.flush()

        threading.Thread(target=pump, name="pump-frontend", daemon=True).start()

        # 等待前端就绪
        deadline = time.time() + args.timeout
        ready = False
        while time.time() < deadline and proc.poll() is None:
            if port_open(FRONTEND_PORT):
                ready = True
                break
            time.sleep(0.5)
        if not ready:
            log("前端启动超时或已退出，请查看上方日志。", color="red")
            return 1

    demo_url = f"http://localhost:{FRONTEND_PORT}/#/demo"
    log("=" * 60)
    log("前端已就绪：")
    log(f"  演示页面  {demo_url}", color="cyan")
    log(f"  项目入口  http://localhost:{FRONTEND_PORT}/", color="cyan")
    log("=" * 60)

    if not args.no_browser:
        open_browser(demo_url)

    try:
        while True:
            time.sleep(0.5)
            if proc is not None and proc.poll() is not None:
                log(f"前端进程已退出（code={proc.returncode}）。", color="yellow")
                break
    except KeyboardInterrupt:
        log("收到 Ctrl+C，正在关闭前端...", color="yellow")
        if proc is not None:
            try:
                proc.terminate()
            except OSError:
                pass
        log("已停止。", color="green")

    return 0


if __name__ == "__main__":
    sys.exit(main())