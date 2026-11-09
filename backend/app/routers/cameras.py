"""摄像头设备管理：CRUD + 连通性测试"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Camera
from ..schemas import (
    CameraCreate,
    CameraOut,
    CameraTestRequest,
    CameraTestResult,
    CameraUpdate,
    MessageOut,
)

router = APIRouter()


@router.post("/test", response_model=CameraTestResult)
def test_connection(body: CameraTestRequest):
    """试拉 RTSP 流验证连通性（6 秒超时），供后台"测试连接"按钮使用。

    在独立线程中探测，避免阻塞事件循环；返回可读的中文结果。
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

    def _probe(url: str) -> CameraTestResult:
        import cv2

        cap = cv2.VideoCapture(url)
        # 部分后端支持 OpenCV 打开/读取超时（尽力设置，不可达地址仍由外层超时兜底）
        try:
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 4000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 4000)
        except Exception:
            pass
        if not cap.isOpened():
            cap.release()
            return CameraTestResult(
                ok=False,
                message="无法打开流：请检查地址、端口、账号密码，或摄像头未通电/未联网",
            )
        ok, _ = cap.read()
        cap.release()
        if ok:
            return CameraTestResult(ok=True, message="连接成功，可正常拉流")
        return CameraTestResult(
            ok=False, message="已建立连接但读不到画面，请检查摄像头编码输出是否正常"
        )

    # 注意：不能使用 with 块（shutdown 会等待探测线程结束，不可达地址可能阻塞数十秒）
    ex = ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(_probe, body.rtsp_url)
    try:
        return fut.result(timeout=8)
    except FutureTimeout:
        ex.shutdown(wait=False)
        return CameraTestResult(
            ok=False,
            message="连接超时（8 秒）：请确认地址格式 rtsp://账号:密码@IP:554/stream，且本机可访问该网络",
        )


@router.get("", response_model=List[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).order_by(Camera.id).all()


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(body: CameraCreate, db: Session = Depends(get_db)):
    cam = Camera(
        name=body.name,
        location=body.location,
        rtsp_url=body.rtsp_url,
        enabled=body.enabled,
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    return cam


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(
    camera_id: int, body: CameraUpdate, db: Session = Depends(get_db)
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(cam, k, v)
    db.commit()
    db.refresh(cam)
    return cam


@router.delete("/{camera_id}", response_model=MessageOut)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    db.delete(cam)
    db.commit()
    return MessageOut(message="删除成功")


@router.post("/{camera_id}/status", response_model=CameraOut)
def update_status(camera_id: int, status: str, db: Session = Depends(get_db)):
    """YOLO 推理服务心跳，用于更新摄像头在线/离线状态"""
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    cam.status = status
    db.commit()
    db.refresh(cam)
    from ..services.events import bus

    bus.publish(
        "camera_status",
        {
            "id": cam.id,
            "name": cam.name,
            "location": cam.location or "",
            "status": cam.status,
        },
    )
    return cam
