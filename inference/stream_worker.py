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

from .annotate import draw_annotations, draw_zones
from .detector import YoloDetector
from .judge import judge_violations
from .zone import judge_zone_intrusion


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

        # 危险区域（多边形 ROI）：启动时/重连后按摄像头从后端拉取
        self.zones: list = []
        self.zones_loaded_at = 0.0
        self.zones_refresh_seconds = config.get("zones_refresh_seconds", 60)
        # 各区域的"首次进入时间"用于停留时长判定：zone_id -> enter_ts
        self._zone_enter_ts: dict = {}

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
        zones=None,
        hit_zone_ids=None,
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
        # 区域闯入时，叠加绘制危险区域多边形（命中区域高亮）
        if zones:
            anno_image = draw_zones(anno_image, zones, hit_zone_ids)
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

    # ---------- 危险区域配置拉取 ----------
    def _load_zones(self, force: bool = False):
        """按摄像头从后端拉取启用的危险区域配置（定期刷新，失败保留旧配置）"""
        now = time.time()
        if not force and now - self.zones_loaded_at < self.zones_refresh_seconds:
            return
        try:
            resp = requests.get(
                f"{self.backend_url}/api/zones",
                params={"camera_id": self.camera["id"]},
                timeout=8,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.zones = [z for z in data if z.get("enabled", True)]
                self.zones_loaded_at = now
                if self.zones:
                    print(f"[{self.camera['name']}] 已加载危险区域 {len(self.zones)} 个")
        except Exception as e:
            print(f"[{self.camera['name']}] 危险区域拉取失败（沿用旧配置）: {e}")

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
            # 定期拉取危险区域配置（首次连接后立即拉）
            self._load_zones()
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

            # ---------- 危险区域闯入判定（几何 + 置信度 + 停留时长） ----------
            zone_vio_conf = 0.0
            hit_zone_ids = set()
            if self.zones and detections:
                img_h, img_w = frame.shape[:2]
                now_ts = time.time()
                hits = judge_zone_intrusion(
                    detections, self.zones, img_w, img_h
                )
                cur_ids = {h["zone_id"] for h in hits}
                # 维护每个区域的进入时间；离开即清除
                for zid in list(self._zone_enter_ts.keys()):
                    if zid not in cur_ids:
                        self._zone_enter_ts.pop(zid, None)
                for h in hits:
                    zid = h["zone_id"]
                    zone_cfg = next(
                        (z for z in self.zones if z.get("id") == zid), {}
                    )
                    min_dwell = float(zone_cfg.get("min_dwell_seconds", 2.0))
                    enter_ts = self._zone_enter_ts.setdefault(zid, now_ts)
                    dwell = now_ts - enter_ts
                    if dwell >= min_dwell:
                        hit_zone_ids.add(zid)
                        if h["max_conf"] > zone_vio_conf:
                            zone_vio_conf = h["max_conf"]
                if hit_zone_ids:
                    violations.add("zone_intrusion")

            if not violations:
                continue

            # 违规类型 -> 触发该类别的类别名（PPE 与火源规则合并）
            trigger_by_vio = {**self.rule, **self.fire_rule}
            # 每条违规的置信度：触发该违规的检测框最大置信度（direct 模式）
            for vio in violations:
                if vio == "zone_intrusion":
                    conf = zone_vio_conf
                    self._report(
                        vio, frame, conf, all_detections,
                        zones=self.zones, hit_zone_ids=hit_zone_ids,
                    )
                    continue
                trigger_cls = trigger_by_vio.get(vio, "")
                conf = max(
                    (d.conf for d in all_detections if d.cls_name == trigger_cls),
                    default=0.0,
                )
                self._report(vio, frame, conf, all_detections)

    def stop(self):
        self._running = False
