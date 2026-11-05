"""YOLO 检测器封装（与 inference/detector.py 保持一致）

临时演示模式由后端直接加载模型推理，避免走 RTSP/推理服务链路。
"""
from typing import List

from ultralytics import YOLO


class Detection:
    """单个检测目标"""

    def __init__(self, cls_id: int, cls_name: str, conf: float, box: List[float]):
        self.cls_id = cls_id
        self.cls_name = cls_name
        self.conf = conf
        # box: [x1, y1, x2, y2]
        self.box = box


class YoloDetector:
    def __init__(self, model_path: str, conf_threshold: float = 0.5, device: str = "cpu"):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = device
        # 类别索引 -> 名称映射
        self.names = self.model.names  # dict: idx -> name

    def predict(self, image) -> List[Detection]:
        """输入 BGR 图像，返回 Detection 列表"""
        results = self.model.predict(
            source=image,
            conf=self.conf_threshold,
            device=self.device,
            verbose=False,
        )
        detections: List[Detection] = []
        if not results:
            return detections
        r = results[0]
        if r.boxes is None:
            return detections
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    cls_id=cls_id,
                    cls_name=self.names.get(cls_id, str(cls_id)),
                    conf=conf,
                    box=[x1, y1, x2, y2],
                )
            )
        return detections
