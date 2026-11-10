"""危险区域（多边形 ROI）闯入判定（与 backend/app/detection/zone.py 双份同步，勿单改）

原理：用人员检测框的"落脚点"（框底中点 = 脚下位置）判断是否落在危险多边形内，
结合置信度阈值与停留时长，避免"路过边缘"的误报。

- point_in_polygon：射线法内点判定（纯 Python，无第三方依赖）
- foot_point：取检测框底边中点
- judge_zone_intrusion：纯函数，按本次帧检测结果返回命中的区域列表
  （停留时长由调用方按时间累积状态维护，本模块只提供几何与时序辅助）

坐标约定：polygon 为归一化坐标 [[x,y],...]（0~1）；检测框为像素坐标 (x1,y1,x2,y2)。
判定前把落脚点用画面尺寸归一化，与 polygon 同为 0~1 域比较。
"""
from typing import Dict, List, Optional, Tuple

from .detector import Detection


def point_in_polygon(px: float, py: float, polygon: List[List[float]]) -> bool:
    """射线法：判断点 (px,py) 是否在多边形内。polygon 为 [[x,y],...]。"""
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        # 判断水平射线与边 (i,j) 是否相交
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def foot_point(box: List[float], img_w: float, img_h: float) -> Tuple[float, float]:
    """检测框底边中点（脚下位置），并归一化到 0~1。box=[x1,y1,x2,y2]。"""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2.0
    fy = y2  # 底边
    if img_w <= 0 or img_h <= 0:
        return 0.0, 0.0
    return cx / img_w, fy / img_h


def judge_zone_intrusion(
    detections: List[Detection],
    zones: List[Dict],
    img_w: float,
    img_h: float,
) -> List[Dict]:
    """判断本帧有哪些区域被人员闯入（几何 + 置信度；不含停留时长）。

    :param detections: 本帧检测结果（含 cls_name/conf/box）
    :param zones: 区域配置列表，每项含：
        {id, zone_name, zone_type, points:[[x,y],...], min_confidence}
    :return: 命中区域列表 [{zone_id, zone_name, zone_type, max_conf}, ...]
    """
    persons = [
        d for d in detections if d.cls_name.lower() == "person"
    ]
    if not persons or not zones:
        return []

    hits: List[Dict] = []
    for zone in zones:
        pts = zone.get("points") or []
        if len(pts) < 3:
            continue
        min_conf = float(zone.get("min_confidence", 0.4))
        best_conf = 0.0
        matched = False
        for p in persons:
            if p.conf < min_conf:
                continue
            fx, fy = foot_point(p.box, img_w, img_h)
            if point_in_polygon(fx, fy, pts):
                matched = True
                if p.conf > best_conf:
                    best_conf = p.conf
        if matched:
            hits.append(
                {
                    "zone_id": zone.get("id"),
                    "zone_name": zone.get("zone_name", ""),
                    "zone_type": zone.get("zone_type", "danger"),
                    "max_conf": best_conf,
                }
            )
    return hits
