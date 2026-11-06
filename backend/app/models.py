"""SQLAlchemy ORM 模型"""
import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from .database import Base

# 时间戳统一用 Python 本地时间写入（不用 server_default 的 CURRENT_TIMESTAMP：
# SQLite 的 CURRENT_TIMESTAMP 是 UTC，与业务层的本地时间比较会差 8 小时）
_ts = datetime.now


class Camera(Base):
    """监控摄像头设备"""

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, comment="摄像头名称")
    location = Column(String(128), default="", comment="安装点位")
    rtsp_url = Column(String(512), nullable=False, comment="RTSP 拉流地址")
    status = Column(String(16), default="offline", comment="online/offline")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=_ts, comment="创建时间")


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
    anno_url = Column(String(512), default="", comment="标注证据图地址（含检测框）")
    detections_json = Column(Text, default="", comment="该帧全部检测目标 JSON（详情展示用）")
    created_at = Column(DateTime, default=_ts, index=True, comment="抓拍时间")

    @property
    def detections(self) -> list | None:
        """解析 detections_json；为空或非法时返回 None"""
        if not self.detections_json:
            return None
        try:
            data = json.loads(self.detections_json)
            return data if isinstance(data, list) else None
        except (json.JSONDecodeError, TypeError):
            return None


class WarningRule(Base):
    """预警规则：某摄像头（或全部）某类型（或全部）在时间窗口内违规次数达到阈值即触发"""

    __tablename__ = "warning_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, comment="规则名称")
    camera_id = Column(Integer, nullable=True, comment="摄像头ID（空=全部摄像头）")
    violation_type = Column(
        String(32), nullable=True, comment="违规类型（空=全部类型）"
    )
    threshold = Column(Integer, nullable=False, default=3, comment="窗口内违规次数阈值")
    window_minutes = Column(Integer, nullable=False, default=60, comment="统计时间窗口（分钟）")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime, default=_ts, comment="创建时间")


class WarningEvent(Base):
    """预警事件（规则触发后生成，前端铃铛/预警中心展示）"""

    __tablename__ = "warning_events"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, nullable=True, comment="触发规则的 ID")
    camera_id = Column(Integer, default=0, index=True, comment="摄像头ID")
    camera_name = Column(String(64), default="", comment="摄像头名称")
    violation_type = Column(String(32), default="", comment="违规类型")
    count = Column(Integer, nullable=False, default=0, comment="窗口内违规次数")
    triggered_at = Column(DateTime, default=_ts, index=True, comment="触发时间")
    is_read = Column(Boolean, nullable=False, default=False, comment="是否已读")
