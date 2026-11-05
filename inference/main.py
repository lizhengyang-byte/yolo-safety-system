"""YOLO 推理服务入口

启动流程：
1. 从 FastAPI 后端拉取启用的摄像头列表
2. 为每个摄像头启动一个 StreamWorker 线程
3. 支持信号退出
"""
import os
import signal
import sys
import threading
import time

import requests
import yaml

from .stream_worker import StreamWorker

# 本地开发可用 CONFIG_PATH=config.local.yaml 覆盖（默认 config.yaml 面向 docker）
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_cameras(config: dict) -> list:
    """从后端获取启用中的摄像头"""
    url = f"{config['backend_url'].rstrip('/')}/api/cameras"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    cams = resp.json()
    return [c for c in cams if c.get("enabled", True)]


def main():
    config = load_config()
    print("[YOLO推理服务] 配置加载完成")
    try:
        cameras = fetch_cameras(config)
    except Exception as e:
        print(f"[YOLO推理服务] 获取摄像头列表失败: {e}")
        print("提示：请先启动 FastAPI 后端，并在后台录入摄像头。")
        cameras = []

    if not cameras:
        print("[YOLO推理服务] 当前无启用的摄像头，服务退出。")
        sys.exit(0)

    workers = []
    for cam in cameras:
        w = StreamWorker(cam, config)
        t = threading.Thread(target=w.run, daemon=True, name=f"worker-cam{cam['id']}")
        t.start()
        workers.append((w, t))
        print(f"[YOLO推理服务] 已启动摄像头 {cam['name']} (id={cam['id']})")

    def _stop(sig, frame):
        print("\n[YOLO推理服务] 正在退出...")
        for w, _ in workers:
            w.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        _stop(None, None)


if __name__ == "__main__":
    main()
