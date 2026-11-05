"""违规记录：YOLO 上报 + 查询分页 + 图片访问"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Violation
from ..schemas import ViolationCreate, ViolationOut, ViolationPage

router = APIRouter()


@router.post("", response_model=ViolationOut, status_code=201)
def report_violation(body: ViolationCreate, db: Session = Depends(get_db)):
    """YOLO 推理服务检测到违规后调用，图片已提前存到 UPLOAD_DIR，
    这里只记录元数据并生成 image_url。"""
    image_path = body.camera_name or "unknown"
    image_url = ""  # 由前端上传接口或推理服务补充
    v = Violation(
        camera_id=body.camera_id,
        camera_name=body.camera_name,
        violation_type=body.violation_type,
        confidence=body.confidence,
        image_path=image_path,
        image_url=image_url,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.post("/with-image", response_model=ViolationOut, status_code=201)
async def report_violation_with_image(
    file: bytes = ...,
    camera_id: int = Query(...),
    camera_name: str = Query(""),
    violation_type: str = Query(...),
    confidence: float = Query(0.0),
    db: Session = Depends(get_db),
):
    """YOLO 服务直接 POST 图片二进制 + 违规信息，后端保存图片并入库。
    前端表单需用 multipart/form-data。"""
    import datetime
    from ..config import settings

    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    fname = f"v_{camera_id}_{now}.jpg"
    path = f"{settings.UPLOAD_DIR}/{fname}"
    with open(path, "wb") as f:
        f.write(file)

    v = Violation(
        camera_id=camera_id,
        camera_name=camera_name,
        violation_type=violation_type,
        confidence=confidence,
        image_path=path,
        image_url=f"/images/{fname}",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
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
