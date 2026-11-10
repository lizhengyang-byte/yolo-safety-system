"""RTSP 拉流 + YOLO 检测 + 违规抓拍上报 Worker

职责：
1. 通过 OpenCV 拉取摄像头 RTSP 流（先经 MediaMTX 转发保证稳定）
2. 周期性送入 YOLO 检测
3. 判定违规，命中时截图保存并调用后端接口上报（原始帧 + 标注证据图）
4. 处理断流重连
"""
import io
import json
import os
import time

import cv2
import numpy as np
import requests

from .annotate import draw_annotations
from .detector import YoloDetector
from .judge import judge_violations


class StreamWorker:
    def __init__(self, camera: dict, config: dict):
        self.camera = camera  # {"id":1, "name":"", "rtsp_url":""}
        self.config = config
        self.backend_url = config["backend_url"].rstrip("/")
        self.detector = YoloDetector(
            model_path=config["model_path"],
            conf_threshold=config.get("conf_threshold", 0.5),
            device=config.get("device", "cpu"),
        )
        self.rule = config.get("violation_rule", {})
        self.judge_mode = config.get("judge_mode", "direct")

        # ---------- 火源/烟雾检测（第二模型，与 PPE 并行；每个摄像头都检测）----------
        self.fire_enabled = config.get("fire_enabled", False)
        self.fire_detector = None
        self.fire_rule = config.get("fire_violation_rule", {})
        if self.fire_enabled and config.get("fire_model_path"):
            try:
                self.fire_detector = YoloDetector(
                    model_path=config["fire_model_path"],
                    conf_threshold=config.get("fire_conf_threshold", 0.4),
                    device=config.get("device", "cpu"),
                )
            except Exception as e:
                print(f"[{camera.get('name', camera.get('id'))}] 火源模型加载失败，仅运行 PPE 检测: {e}")
                self.fire_detector = None

        self.dedup_seconds = config.get("dedup_seconds", 30)
        self.infer_every = config.get("infer_every_n_frames", 5)
        self.save_dir = config.get("save_dir", "/data/images")
        os.makedirs(self.save_dir, exist_ok=True)

        # 违规去重缓存: (violation_type) -> last_ts
        self._last_report: dict = {}
        self._running = False

    # ---------- 上报 ----------
    def _report(
        self,
        vio_type: str,
        image_np: np.ndarray,
        confidence: float = 0.0,
        detections=None,
    ):
        now = time.time()
        key = vio_type
        if now - self._last_report.get(key, 0) < self.dedup_seconds:
            return
        self._last_report[key] = now

        # 保存本地图片（原始帧 + 标注证据图）
        ts = time.strftime("%Y%m%d%H%M%S")
        fname = f"cam{self.camera['id']}_{vio_type}_{ts}.jpg"
        anno_fname = f"cam{self.camera['id']}_{vio_type}_{ts}_anno.jpg"
        local_path = os.path.join(self.save_dir, fname)
        cv2.imwrite(local_path, image_np)

        # 标注证据图：检测框 + 违规横幅（有说服力的留痕）
        anno_image = draw_annotations(image_np, detections or [], [vio_type])
        anno_local = os.path.join(self.save_dir, anno_fname)
        cv2.imwrite(anno_local, anno_image)

        # 组装图片字节
        ok, buf = cv2.imencode(".jpg", image_np)
        if not ok:
            return
        image_bytes = buf.tobytes()
        ok_anno, buf_anno = cv2.imencode(".jpg", anno_image)
        if not ok_anno:
            return
        anno_bytes = buf_anno.tobytes()

        # 该帧全部检测目标 JSON（违规详情页展示用）
        detections_json = ""
        if detections:
            detections_json = json.dumps(
                [
                    {
                        "cls_id": d.cls_id,
                        "cls_name": d.cls_name,
                        "conf": round(d.conf, 3),
                        "box": [round(x, 1) for x in d.box],
                    }
                    for d in detections
                ]
            )

        # POST multipart 图片 + 元数据（推荐，后端同时入库）
        try:
            resp = requests.post(
                f"{self.backend_url}/api/violations/with-image",
                files={
                    "file": (fname, image_bytes, "image/jpeg"),
                    "anno": (anno_fname, anno_bytes, "image/jpeg"),
                },
                data={
                    "camera_id": self.camera["id"],
                    "camera_name": self.camera["name"],
                    "violation_type": vio_type,
                    "confidence": f"{confidence:.3f}",
                    "detections": detections_json,
                },
                timeout=10,
            )
            if resp.status_code == 201:
                print(f"[{self.camera['name']}] 上报违规 {vio_type}: {local_path}")
            else:
                print(f"[{self.camera['name']}] 上报失败 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[{self.camera['name']}] 上报异常: {e}")

    # ---------- 心跳：更新摄像头在线状态 ----------
    def _heartbeat(self, online: bool):
        try:
            requests.post(
                f"{self.backend_url}/api/cameras/{self.camera['id']}/status",
                params={"status": "online" if online else "offline"},
                timeout=5,
            )
        except Exception:
            pass

    # ---------- 主循环 ----------
    def run(self):
        self._running = True
        cap = None
        frame_idx = 0
        while self._running:
            if cap is None or not cap.isOpened():
                print(f"[{self.camera['name']}] 连接 {self.camera['rtsp_url']} ...")
                cap = cv2.VideoCapture(self.camera["rtsp_url"])
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                time.sleep(1)
                continue

            ret, frame = cap.read()
            if not ret:
                print(f"[{self.camera['name']}] 读取失败，尝试重连")
                cap.release()
                cap = None
                self._heartbeat(False)
                time.sleep(2)
                continue

            self._heartbeat(True)
            frame_idx += 1
            if frame_idx % self.infer_every != 0:
                continue

            try:
                detections = self.detector.predict(frame)
            except Exception as e:
                print(f"[{self.camera['name']}] 检测异常: {e}")
                continue

            # 火源/烟雾检测（第二模型并行，失败不影响 PPE 链路）
            fire_detections = []
            if self.fire_detector is not None:
                try:
                    fire_detections = self.fire_detector.predict(frame)
                except Exception as e:
                    print(f"[{self.camera['name']}] 火源检测异常: {e}")

            # 合并两类检测结果用于标注与明细
            all_detections = detections + fire_detections

            violations = judge_violations(
                detections, self.rule, mode=self.judge_mode
            )
            if self.fire_detector is not None and self.fire_rule:
                violations |= judge_violations(
                    fire_detections, self.fire_rule, mode="direct"
                )

            if not violations:
                continue

            # 违规类型 -> 触发该类别的类别名（PPE 与火源规则合并）
            trigger_by_vio = {**self.rule, **self.fire_rule}
            # 每条违规的置信度：触发该违规的检测框最大置信度（direct 模式）
            for vio in violations:
                trigger_cls = trigger_by_vio.get(vio, "")
                conf = max(
                    (d.conf for d in all_detections if d.cls_name == trigger_cls),
                    default=0.0,
                )
                self._report(vio, frame, conf, all_detections)

    def stop(self):
        self._running = False
