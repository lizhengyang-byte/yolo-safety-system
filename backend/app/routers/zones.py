"""危险区域（多边形 ROI）管理——绑定到具体摄像头

每个区域用归一化多边形顶点（0~1）定义，推理服务按摄像头拉取本区域配置，
对 Person 检测框落脚点做内点判定，结合置信度 + 停留时长判为"危险区域闯入"。
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DangerZone
from ..schemas import (
    DangerZoneCreate,
    DangerZoneOut,
    DangerZoneUpdate,
    MessageOut,
)

router = APIRouter()


def _to_out(z: DangerZone) -> DangerZoneOut:
    return DangerZoneOut(
        id=z.id,
        camera_id=z.camera_id,
        zone_name=z.zone_name,
        zone_type=z.zone_type,
        polygon=z.points,
        min_confidence=z.min_confidence,
        min_dwell_seconds=z.min_dwell_seconds,
        enabled=z.enabled,
        created_at=z.created_at,
    )


def _validate_polygon(points: List[List[float]]) -> str:
    """校验并序列化多边形：至少 3 个点，坐标 0~1"""
    if not points or len(points) < 3:
        raise HTTPException(status_code=400, detail="多边形至少需要 3 个顶点")
    clean = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise HTTPException(status_code=400, detail="顶点格式应为 [x, y]")
        x, y = float(p[0]), float(p[1])
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise HTTPException(status_code=400, detail="顶点坐标须为 0~1 的归一化值")
        clean.append([round(x, 5), round(y, 5)])
    return json.dumps(clean)


@router.get("", response_model=List[DangerZoneOut])
def list_zones(
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """列出危险区域；可按 camera_id 过滤"""
    q = db.query(DangerZone)
    if camera_id is not None:
        q = q.filter(DangerZone.camera_id == camera_id)
    return [_to_out(z) for z in q.order_by(DangerZone.id).all()]


@router.post("", response_model=DangerZoneOut, status_code=201)
def create_zone(body: DangerZoneCreate, db: Session = Depends(get_db)):
    poly = _validate_polygon(body.polygon)
    z = DangerZone(
        camera_id=body.camera_id,
        zone_name=body.zone_name,
        zone_type=body.zone_type or "danger",
        polygon=poly,
        min_confidence=body.min_confidence,
        min_dwell_seconds=body.min_dwell_seconds,
        enabled=body.enabled,
    )
    db.add(z)
    db.commit()
    db.refresh(z)
    return _to_out(z)


@router.put("/{zone_id}", response_model=DangerZoneOut)
def update_zone(
    zone_id: int, body: DangerZoneUpdate, db: Session = Depends(get_db)
):
    z = db.get(DangerZone, zone_id)
    if z is None:
        raise HTTPException(status_code=404, detail="区域不存在")
    data = body.model_dump(exclude_unset=True)
    if "polygon" in data and data["polygon"] is not None:
        data["polygon"] = _validate_polygon(data["polygon"])
    for k, v in data.items():
        if v is not None or k in ("camera_id", "enabled"):
            setattr(z, k, v)
    db.commit()
    db.refresh(z)
    return _to_out(z)


@router.delete("/{zone_id}", response_model=MessageOut)
def delete_zone(zone_id: int, db: Session = Depends(get_db)):
    z = db.get(DangerZone, zone_id)
    if z is None:
        raise HTTPException(status_code=404, detail="区域不存在")
    db.delete(z)
    db.commit()
    return MessageOut(message="删除成功")
