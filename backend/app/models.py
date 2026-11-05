"""SQLAlchemy ORM 模型"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.sql import func as _func

from .database import Base


class Camera(Base):
    """监控摄像头设备"""

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, comment="摄像头名称")
    location = Column(String(128), default="", comment="安装点位")
    rtsp_url = Column(String(512), nullable=False, comment="RTSP 拉流地址")
    status = Column(String(16), default="offline", comment="online/offline")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=_func.now(), comment="创建时间")


class Violation(Base):
    """违规抓拍记录（安全日志）"""

    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, index=True, comment="摄像头ID")
    camera_name = Column(String(64), default="", comment="摄像头名称")
    violation_type = Column(String(32), index=True, comment="违规类型")
    confidence = Column(Float, default=0.0, comment="识别置信度")
    image_path = Column(String(512), comment="图片存储路径")
    image_url = Column(String(512), comment="图片访问地址")
    created_at = Column(DateTime, server_default=_func.now(), index=True, comment="抓拍时间")
