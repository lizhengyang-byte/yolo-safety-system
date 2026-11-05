"""摄像头设备管理：CRUD"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Camera
from ..schemas import CameraCreate, CameraOut, CameraUpdate, MessageOut

router = APIRouter()


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
    return cam
