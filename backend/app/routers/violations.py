"""违规记录：YOLO 上报 + 查询分页 + 图片访问"""
import datetime
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Violation
from ..schemas import ViolationCreate, ViolationOut, ViolationPage
from ..services.warnings import trigger_warning_check

router = APIRouter()


@router.post("", response_model=ViolationOut, status_code=201)
def report_violation(body: ViolationCreate, db: Session = Depends(get_db)):
    """YOLO 推理服务检测到违规后调用（仅记录元数据，图片已另存）。"""
    v = Violation(
        camera_id=body.camera_id,
        camera_name=body.camera_name,
        violation_type=body.violation_type,
        confidence=body.confidence,
        image_path="",
        image_url="",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    # 预警规则检查（commit 后统计，需包含刚入库记录）
    trigger_warning_check(db, body.camera_id, body.camera_name, body.violation_type)
    return v


@router.post("/with-image", response_model=ViolationOut, status_code=201)
async def report_violation_with_image(
    file: UploadFile = File(...),
    anno: UploadFile = File(None),
    detections: str = Form(""),
    camera_id: int = Form(...),
    camera_name: str = Form(""),
    violation_type: str = Form(...),
    confidence: float = Form(0.0),
    db: Session = Depends(get_db),
):
    """YOLO 服务直接 POST 图片(multipart) + 违规信息，后端保存图片并入库。

    - file：原始帧（image_url）
    - anno：标注证据图（anno_url，可选；推理服务已绘制检测框）
    - detections：该帧全部检测目标 JSON（可选，违规详情页展示用）

    注意：camera_id 等字段必须用 Form（multipart 表单字段），
    前端/推理服务用 files+data 提交即命中本接口。
    """
    raw = await file.read()
    # 毫秒级时间戳，避免同一摄像头同一秒内多次抓拍互相覆盖
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    fname = f"v_{camera_id}_{now}.jpg"
    path = f"{settings.UPLOAD_DIR}/{fname}"
    with open(path, "wb") as f:
        f.write(raw)

    anno_url = ""
    if anno is not None:
        anno_raw = await anno.read()
        anno_fname = f"v_{camera_id}_{now}_anno.jpg"
        anno_path = f"{settings.UPLOAD_DIR}/{anno_fname}"
        with open(anno_path, "wb") as f:
            f.write(anno_raw)
        anno_url = f"/images/{anno_fname}"

    # 校验 detections JSON；非法则忽略，不影响上报
    detections_json = ""
    if detections:
        try:
            json.loads(detections)
            detections_json = detections
        except (json.JSONDecodeError, TypeError):
            detections_json = ""

    v = Violation(
        camera_id=camera_id,
        camera_name=camera_name,
        violation_type=violation_type,
        confidence=confidence,
        image_path=path,
        image_url=f"/images/{fname}",
        anno_url=anno_url,
        detections_json=detections_json,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    # 预警规则检查（commit 后统计，需包含刚入库记录）
    trigger_warning_check(db, camera_id, camera_name, violation_type)
    return v


@router.get("", response_model=ViolationPage)
def list_violations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    violation_type: Optional[str] = Query(None),
    camera_id: Optional[int] = Query(None),
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    q = db.query(Violation)
    if violation_type:
        q = q.filter(Violation.violation_type == violation_type)
    if camera_id:
        q = q.filter(Violation.camera_id == camera_id)
    if start:
        q = q.filter(Violation.created_at >= f"{start} 00:00:00")
    if end:
        q = q.filter(Violation.created_at <= f"{end} 23:59:59")

    total = q.count()
    items = (
        q.order_by(Violation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ViolationPage(total=total, items=items)
