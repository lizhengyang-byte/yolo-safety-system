"""临时演示：直接调用笔记本摄像头（前端 getUserMedia 取帧）进行实时检测

流程与正式链路一致：YOLO 检测 -> 违规判定 -> 抓拍留痕入库。
仅绕过 RTSP/推理服务，由后端直接推理，用于现场演示。
"""
import os
from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..detection.detector import YoloDetector
from ..detection.judge import judge_violations
from ..models import Violation

router = APIRouter()

# 全局懒加载检测器单例，避免每次请求重复加载模型
_detector: YoloDetector | None = None


def get_detector() -> YoloDetector:
    global _detector
    if _detector is None:
        if not os.path.exists(settings.DEMO_MODEL_PATH):
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "未找到演示模型，请将 best.pt 放入 "
                    f"{settings.DEMO_MODEL_PATH} 目录后重启后端"
                ),
            )
        _detector = YoloDetector(
            model_path=settings.DEMO_MODEL_PATH,
            conf_threshold=settings.DEMO_CONF_THRESHOLD,
            device=settings.DEMO_DEVICE,
        )
    return _detector


@router.post("/detect")
async def demo_detect(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """接收前端摄像头帧（JPEG），返回检测框 + 违规类型；违规时自动抓拍入库。"""
    raw = await file.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    try:
        import cv2

        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        img = None
    if img is None:
        raise HTTPException(status_code=400, detail="图片解码失败")

    detections = get_detector().predict(img)
    violations = judge_violations(detections, settings.VIOLATION_RULE)

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

    # 违规 -> 自动抓拍留痕 + 入库（camera_id=0 表示演示来源）
    if violations:
        ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        fname = f"demo_{ts}.jpg"
        path = os.path.join(settings.UPLOAD_DIR, fname)
        cv2.imwrite(path, img)

        # 主违规类型取排序后第一个，保持与正式记录单值类型一致
        persons_conf = [
            d.conf for d in detections if d.cls_name == "person"
        ]
        v = Violation(
            camera_id=0,
            camera_name="临时演示",
            violation_type=sorted(violations)[0],
            confidence=round(max(persons_conf), 3) if persons_conf else 0.0,
            image_path=path,
            image_url=f"/images/{fname}",
        )
        db.add(v)
        db.commit()
        result["snapshot_url"] = f"/images/{fname}"

    return result
