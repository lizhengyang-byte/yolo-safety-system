"""违规判定：支持两种模式

- direct（默认，适配 ppe.pt）：
    模型直接输出违规类（如 NO-Hardhat / NO-Mask / NO-Safety Vest），
    rule 形如 {"no_helmet": "NO-Hardhat", ...}，出现对应违规类即判定违规。
- person_iou（通用正类装备模型）：
    rule 形如 {"no_helmet": "helmet", ...}，对每个 person 目标，
    若其与对应装备框 IoU 低于阈值，判定该装备缺失。
"""
from typing import Dict, List, Set

from .detector import Detection


def _iou(box_a: List[float], box_b: List[float]) -> float:
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def judge_violations(
    detections: List[Detection],
    rule: Dict[str, str],
    mode: str = "direct",
    iou_threshold: float = 0.3,
) -> Set[str]:
    """根据检测结果判定违规类型集合，返回违规类型 key 集合。"""
    if mode == "direct":
        # 模型直接输出违规类：出现即违规（检测器已按 conf_threshold 过滤）
        names = {d.cls_name for d in detections}
        return {vio for vio, cls in rule.items() if cls in names}

    # person_iou 模式：person 与装备框 IoU 判定
    persons = [d for d in detections if d.cls_name == "person"]
    if not persons:
        return set()

    by_class: Dict[str, List[Detection]] = {}
    for d in detections:
        if d.cls_name == "person":
            continue
        by_class.setdefault(d.cls_name, []).append(d)

    violations: Set[str] = set()
    for person in persons:
        for vio_type, equip_cls in rule.items():
            # 该违规类型已命中则跳过
            if vio_type in violations:
                continue
            equips = by_class.get(equip_cls, [])
            covered = any(
                _iou(person.box, e.box) >= iou_threshold for e in equips
            )
            if not covered:
                violations.add(vio_type)
    return violations
