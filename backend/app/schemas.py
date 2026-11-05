"""Pydantic 请求/响应模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 摄像头 ----------
class CameraBase(BaseModel):
    name: str = Field(..., max_length=64)
    location: str = ""
    rtsp_url: str
    enabled: bool = True


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    rtsp_url: Optional[str] = None
    enabled: Optional[bool] = None


class CameraOut(CameraBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- 违规记录 ----------
class ViolationCreate(BaseModel):
    camera_id: int
    camera_name: str = ""
    violation_type: str
    confidence: float = 0.0


class ViolationOut(BaseModel):
    id: int
    camera_id: int
    camera_name: str
    violation_type: str
    confidence: float
    image_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ViolationPage(BaseModel):
    total: int
    items: List[ViolationOut]


# ---------- 通用 ----------
class MessageOut(BaseModel):
    message: str
