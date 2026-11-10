#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工地AI安全智能监测系统 - 本地快速启动脚本（Python 版）
=====================================================
等价于 start-local.bat，但提供：
  - 健康检查（自动等待后端 / 前端就绪，超时提示）
  - 一键启动/停止（Ctrl+C 优雅关闭所有子进程）
  - 可选启动推理服务（--inference，需先在后台录入摄像头）
  - 单独窗口模式（--windows，默认）或 同一终端内联日志（--inline）

依赖：仓库根目录 .venv（含后端依赖）、frontend/node_modules 已安装。
用法（在仓库根目录执行）：
  python start-local.py               # 启动后端 + 前端
  python start-local.py --inference   # 后端 + 前端 + 推理服务
  python start-local.py --inline      # 同一终端输出日志（Ctrl+C 全部停止）
  python start-local.py --open screen # 启动完成后自动打开智慧大屏
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

# 仓库根目录（脚本所在目录）
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
INFERENCE_CONFIG = "inference/config.local.yaml"
MODEL_CANDIDATES = [ROOT / "weights/ppe/ppe.pt", ROOT / "weights/ppe.pt", ROOT / "inference/weights/ppe.pt"]

BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# 终端颜色（Windows 10+ / ANSI 终端均可用）
COLORS = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "cyan": "\033[96m", "reset": "\033[0m"}


def setup_console() -> None:
    """Windows cmd 默认 GBK 代码页，切换为 UTF-8 避免中文乱码。"""
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


def log(msg: str, color: str = "green", prefix: str = "[启动]") -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    print(f"{COLORS.get(color, '')}{prefix} {msg}{COLORS['reset']}")
    sys.stdout.flush()


def find_python() -> list[str]:
    """优先使用仓库根目录 .venv 的 Python，否则回退到系统 python。"""
    candidates = [
        ROOT / ".venv/Scripts/python.exe",  # Windows
        ROOT / ".venv/bin/python",          # POSIX
    ]
    for path in candidates:
        if path.exists():
            return [str(path)]
    return [sys.executable]


def find_npm() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(port: int, name: str, timeout: float = 60.0) -> bool:
    """轮询等待端口就绪，返回是否成功。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(0.5)
    return False


def start_process(args: list[str], cwd: Path, env: dict | None = None,
                  inline: bool = False, label: str = "", create_console: bool = False) -> subprocess.Popen:
    """启动子进程。

    inline=True 时在同一终端运行，输出重定向到管道（由打印线程输出）；
    create_console=True（仅 Windows）时打开独立窗口，行为与 start-local.bat 一致。
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    kwargs = {"cwd": str(cwd), "env": full_env}
    if inline:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        kwargs["text"] = True
        kwargs["encoding"] = "utf-8"
        kwargs.setdefault("errors", "replace")
    elif os.name == "nt" and create_console:
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]

    proc = subprocess.Popen(args, **kwargs)

    if inline:
        def pump():
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(f"{COLORS['cyan']}[{label}] {line}{COLORS['reset']}")
                sys.stdout.flush()

        threading.Thread(target=pump, name=f"pump-{label}", daemon=True).start()

    return proc


def check_model() -> None:
    if not any(p.exists() for p in MODEL_CANDIDATES):
        log("⚠️  未找到模型权重 ppe.pt（weights/ppe/ 或 weights/）！", color="red")
        log("演示接口会返回 503；请将 ppe.pt 放入 weights/ppe/ 目录。", color="yellow")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="工地AI安全智能监测系统 - 本地快速启动（Python 版）")
    parser.add_argument("--inference", action="store_true",
                        help="同时启动推理服务（需先在后台录入启用摄像头）")
    parser.add_argument("--inline", action="store_true",
                        help="同一终端运行并打印各服务日志（默认：Windows 独立窗口）")
    parser.add_argument("--no-healthcheck", action="store_true",
                        help="启动后不做端口健康检查（默认会等待后端/前端就绪）")
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="健康检查超时秒数（默认 60）")
    parser.add_argument("--open", choices=["none", "dashboard", "screen", "demo"],
                        default="none", help="启动后自动打开的页面（默认 none 不打开）")
    args = parser.parse_args()

    setup_console()

    log("=" * 60)
    log("工地AI安全智能监测系统 - 本地快速启动", color="cyan")
    log("=" * 60)

    # 前置检查
    if not BACKEND_DIR.exists():
        log(f"找不到 backend 目录：{BACKEND_DIR}", color="red")
        return 1
    if not (FRONTEND_DIR / "node_modules").exists():
        log("⚠️  frontend/node_modules 未安装，前端可能启动失败，请先执行 npm install", color="yellow")
    check_model()

    python = find_python()
    npm = find_npm()
    log(f"Python: {python[0]}", color="yellow")
    log(f"npm   : {npm}", color="yellow")

    # 端口占用检查
    if port_open(BACKEND_PORT):
        log(f"端口 {BACKEND_PORT} 已被占用，后端可能已在运行，跳过启动。", color="yellow")
        backend = None
    else:
        log(f"① 启动后端 FastAPI（SQLite，http://localhost:{BACKEND_PORT}）...")
        backend = start_process(
            [*python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
            cwd=BACKEND_DIR, inline=args.inline, label="backend",
            create_console=not args.inline,
        )

    if port_open(FRONTEND_PORT):
        log(f"端口 {FRONTEND_PORT} 已被占用，前端可能已在运行，跳过启动。", color="yellow")
        frontend = None
    else:
        log(f"② 启动前端 Vite（http://localhost:{FRONTEND_PORT}）...")
        frontend = start_process(
            [npm, "run", "dev"],
            cwd=FRONTEND_DIR, inline=args.inline, label="frontend",
            create_console=not args.inline,
        )

    inference = None
    if args.inference:
        if not (ROOT / INFERENCE_CONFIG).exists():
            log(f"找不到推理配置 {INFERENCE_CONFIG}", color="red")
        else:
            log("③ 启动推理服务（RTSP 拉流 + 检测，无启用摄像头时自动退出）...")
            inference = start_process(
                [*python, "-m", "inference.main"],
                cwd=ROOT, inline=args.inline,
                env={"CONFIG_PATH": INFERENCE_CONFIG},
                label="inference", create_console=not args.inline,
            )

    # 健康检查
    if not args.no_healthcheck:
        ok_backend = wait_for_port(BACKEND_PORT, "后端", args.timeout)
        ok_frontend = wait_for_port(FRONTEND_PORT, "前端", args.timeout)

        log("=" * 60)
        log("健康检查结果：", color="cyan")
        log(f"  后端 {BACKEND_PORT}: {'✅ 就绪' if ok_backend else '❌ 超时未就绪'}", color="green" if ok_backend else "red")
        log(f"  前端 {FRONTEND_PORT}: {'✅ 就绪' if ok_frontend else '❌ 超时未就绪'}", color="green" if ok_frontend else "red")
        log("=" * 60)

    log("访问地址：", color="cyan")
    log(f"  后端接口文档  http://localhost:{BACKEND_PORT}/docs", color="cyan")
    log(f"  后台数据看板  http://localhost:{FRONTEND_PORT}/dashboard   (默认账号 admin / admin123)", color="cyan")
    log(f"  智慧大屏      http://localhost:{FRONTEND_PORT}/screen", color="cyan")
    log("  大屏 Kiosk     deploy/start-screen.bat（全屏值班/电视墙）", color="cyan")
    log(f"  临时演示      http://localhost:{FRONTEND_PORT}/demo", color="cyan")
    log("违规图片      http://localhost:8000/images/xxx.jpg", color="cyan")

    # 可选：自动打开指定页面
    if args.open != "none":
        page_path = {"dashboard": "", "screen": "/screen", "demo": "/demo"}[args.open]
        url = f"http://localhost:{FRONTEND_PORT}{page_path}"
        if wait_for_port(FRONTEND_PORT, "前端", 10):
            try:
                import webbrowser

                webbrowser.open(url)
                log(f"已在浏览器打开：{url}", color="cyan")
            except Exception as exc:  # noqa: BLE001
                log(f"自动打开浏览器失败（{exc}），请手动访问 {url}", color="yellow")
        else:
            log(f"前端尚未就绪，请稍后手动访问 {url}", color="yellow")

    if args.inline:
        log("按 Ctrl+C 停止所有服务。", color="yellow")

    # 内联模式：前台等待，Ctrl+C 优雅关闭
    procs = [p for p in (backend, frontend, inference) if p is not None]
    if args.inline and procs:
        try:
            while True:
                time.sleep(0.5)
                # 任一服务退出即提示（不自动退出，便于观察其余服务日志）
                exited = [p for p in procs if p.poll() is not None]
                for p in exited:
                    log(f"服务进程退出（code={p.returncode}）", color="yellow")
                    procs.remove(p)
                if not procs:
                    log("所有服务已退出。", color="yellow")
                    break
        except KeyboardInterrupt:
            log("收到 Ctrl+C，正在关闭所有服务...", color="yellow")
            for p in procs:
                try:
                    p.terminate()
                except OSError:
                    pass
            time.sleep(1)
            for p in procs:
                try:
                    p.kill()
                except OSError:
                    pass
            log("已全部停止。", color="green")

    # 窗口模式：主进程退出，子进程窗口独立存活
    return 0


if __name__ == "__main__":
    sys.exit(main())
