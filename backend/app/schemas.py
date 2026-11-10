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
    anno_url: str = ""
    detections: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ViolationPage(BaseModel):
    total: int
    items: List[ViolationOut]


# ---------- 摄像头连通性测试 ----------
class CameraTestRequest(BaseModel):
    rtsp_url: str


class CameraTestResult(BaseModel):
    ok: bool
    message: str


# ---------- 预警规则 ----------
class WarningRuleBase(BaseModel):
    name: str = Field(..., max_length=64)
    camera_id: Optional[int] = None
    violation_type: Optional[str] = None
    threshold: int = Field(3, ge=1, le=10000)
    window_minutes: int = Field(60, ge=1, le=1440)
    enabled: bool = True


class WarningRuleCreate(WarningRuleBase):
    pass


class WarningRuleUpdate(BaseModel):
    name: Optional[str] = None
    camera_id: Optional[int] = None
    violation_type: Optional[str] = None
    threshold: Optional[int] = Field(None, ge=1, le=10000)
    window_minutes: Optional[int] = Field(None, ge=1, le=1440)
    enabled: Optional[bool] = None


class WarningRuleOut(WarningRuleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class WarningEventOut(BaseModel):
    id: int
    rule_id: Optional[int]
    camera_id: int
    camera_name: str
    violation_type: str
    count: int
    triggered_at: datetime
    is_read: bool

    class Config:
        from_attributes = True


class WarningEventPage(BaseModel):
    total: int
    items: List[WarningEventOut]


# ---------- 通用 ----------
class MessageOut(BaseModel):
    message: str


# ---------- 危险区域（多边形 ROI） ----------
class DangerZoneBase(BaseModel):
    camera_id: int
    zone_name: str = Field(..., max_length=64)
    zone_type: str = "danger"  # danger / pit / lifting / other
    # 归一化多边形顶点 [[x,y],...]，0~1
    polygon: List[List[float]]
    min_confidence: float = Field(0.4, ge=0.0, le=1.0)
    min_dwell_seconds: float = Field(2.0, ge=0.0, le=60.0)
    enabled: bool = True


class DangerZoneCreate(DangerZoneBase):
    pass


class DangerZoneUpdate(BaseModel):
    camera_id: Optional[int] = None
    zone_name: Optional[str] = None
    zone_type: Optional[str] = None
    polygon: Optional[List[List[float]]] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_dwell_seconds: Optional[float] = Field(None, ge=0.0, le=60.0)
    enabled: Optional[bool] = None


class DangerZoneOut(BaseModel):
    id: int
    camera_id: int
    zone_name: str
    zone_type: str
    polygon: List[List[float]]
    min_confidence: float
    min_dwell_seconds: float
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True
