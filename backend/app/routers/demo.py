"""临时演示：直接调用笔记本摄像头（前端 getUserMedia 取帧）进行实时检测

流程与正式链路一致：YOLO 检测 -> 违规判定 -> 抓拍留痕入库（原始帧 + 标注证据图）。
仅绕过 RTSP/推理服务，由后端直接推理，用于现场演示。

能力：
- /api/demo/status  演示环境自检（模型是否已加载等）
- /api/demo/detect  帧检测；no_save=True 时不入库（实时监控叠加复用）；
                     conf 参数覆盖置信度阈值（演示页"灵敏度"滑块）
"""
import json
import os
import threading
from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..detection.annotate import draw_annotations
from ..detection.detector import YoloDetector
from ..detection.judge import judge_violations
from ..models import Violation
from ..services.events import bus
from ..services.warnings import trigger_warning_check

router = APIRouter()

# 全局懒加载检测器单例 + 初始化锁（避免并发首请求重复加载模型）
_detector: YoloDetector | None = None
_detector_lock = threading.Lock()


def _find_model_path() -> str:
    """定位演示模型（ppe.pt）：优先环境变量配置，其次按常见相对路径搜索。

    覆盖 docker（/app/weights/ppe.pt）与本地开发（backend/ 或仓库根目录启动）两种场景。
    """
    candidates = [
        settings.DEMO_MODEL_PATH,
        "weights/ppe.pt",
        "../inference/weights/ppe.pt",
        "inference/weights/ppe.pt",
        "yolo-safety-system/inference/weights/ppe.pt",
        "../ppe.pt",
        "ppe.pt",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return settings.DEMO_MODEL_PATH


def get_detector() -> YoloDetector:
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                path = _find_model_path()
                if not os.path.exists(path):
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "未找到演示模型 ppe.pt，请将模型放入 "
                            f"{settings.DEMO_MODEL_PATH} 或仓库内 inference/weights/ 目录后重启后端"
                        ),
                    )
                _detector = YoloDetector(
                    model_path=path,
                    conf_threshold=settings.DEMO_CONF_THRESHOLD,
                    device=settings.DEMO_DEVICE,
                )
    return _detector


@router.get("/status")
def demo_status():
    """演示环境状态：模型是否已加载 / 模型路径 / 设备 / 默认阈值（环境自检用）"""
    path = _find_model_path()
    return {
        "model_loaded": _detector is not None,
        "model_path": path if os.path.exists(path) else None,
        "device": settings.DEMO_DEVICE,
        "conf_threshold": settings.DEMO_CONF_THRESHOLD,
    }


@router.post("/detect")
async def demo_detect(
    file: UploadFile = File(...),
    no_save: bool = Form(False),
    conf: float = Form(None),
    db: Session = Depends(get_db),
):
    """接收前端摄像头帧（JPEG），返回检测框 + 违规类型；违规时自动抓拍入库。

    - no_save=True：只返回检测结果，不抓拍不入库（实时监控页 AI 叠加复用本接口）
    - conf：本次请求的置信度阈值覆盖（演示页"灵敏度"滑块，None 用默认值）
    """
    raw = await file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    try:
        import cv2

        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        img = None
    if img is None:
        raise HTTPException(status_code=400, detail="图片解码失败")

    detector = get_detector()
    # 同步推理放入线程池，避免阻塞事件循环（并发时登录/心跳等接口仍可响应）
    detections = await run_in_threadpool(detector.predict, img, conf or None)

    violations = judge_violations(
        detections, settings.VIOLATION_RULE, mode=settings.JUDGE_MODE
    )

    result = {
        "detections": [
            {
                "cls_id": d.cls_id,
                "cls_name": d.cls_name,
                "conf": round(d.conf, 3),
                "box": [round(x, 1) for x in d.box],
            }
            for d in detections
        ],
        "violations": sorted(violations),
        "snapshot_url": None,
    }

    # 无违规或仅需检测（监控叠加）时不抓拍
    if not violations or no_save:
        return result

    # 违规 -> 自动抓拍留痕（原始帧 + 标注证据图）+ 入库（camera_id=0 表示演示来源）
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    fname = f"demo_{ts}.jpg"
    anno_fname = f"demo_{ts}_anno.jpg"
    path = os.path.join(settings.UPLOAD_DIR, fname)
    anno_path = os.path.join(settings.UPLOAD_DIR, anno_fname)
    cv2.imwrite(path, img)
    anno_img = draw_annotations(img, detections, sorted(violations))
    cv2.imwrite(anno_path, anno_img)

    # 主违规类型取排序后第一个，保持与正式记录单值类型一致；
    # 置信度取触发违规的检测框（如 NO-Hardhat）的最大置信度
    trigger_classes = {
        settings.VIOLATION_RULE[v] for v in violations if v in settings.VIOLATION_RULE
    }
    vio_conf = [d.conf for d in detections if d.cls_name in trigger_classes]
    v = Violation(
        camera_id=0,
        camera_name="临时演示",
        violation_type=sorted(violations)[0],
        confidence=round(max(vio_conf), 3) if vio_conf else 0.0,
        image_path=path,
        image_url=f"/images/{fname}",
        anno_url=f"/images/{anno_fname}",
        detections_json=json.dumps(result["detections"]),
    )
    db.add(v)
    db.commit()
    # 预警规则检查（commit 后统计，需包含刚入库记录）
    trigger_warning_check(db, 0, "临时演示", sorted(violations)[0])
    bus.publish(
        "violation",
        {
            "id": v.id,
            "camera_id": 0,
            "camera_name": "临时演示",
            "location": "",
            "violation_type": v.violation_type,
            "confidence": round(float(v.confidence or 0), 3),
            "image_url": v.image_url or "",
            "anno_url": v.anno_url or "",
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if v.created_at
            else "",
        },
    )
    # 返回标注证据图作为抓拍展示（更有说服力）
    result["snapshot_url"] = f"/images/{anno_fname}"

    return result
