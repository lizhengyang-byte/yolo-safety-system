"""预警触发服务：违规入库后自动检查规则并生成预警事件

触发时机：violations.py / demo.py 在违规记录 commit 之后调用
`trigger_warning_check(db, camera_id, camera_name, violation_type)`。

规则匹配：enabled AND（camera_id 为空匹配全部，否则必须相等）AND
（violation_type 为空匹配全部类型，否则必须相等）。
防重复：同一摄像头 + 同一类型在最近 10 分钟内已触发过事件则跳过，
避免持续违规时预警刷屏（事件只记录"窗口内累计次数"）。
"""
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Violation, WarningEvent, WarningRule

# 同 camera + type 触发事件的静默窗口（分钟），窗口内已触发则不重复生成
EVENT_COOLDOWN_MINUTES = 10


def _rule_matches(rule: WarningRule, camera_id: int, violation_type: str) -> bool:
    if not rule.enabled:
        return False
    if rule.camera_id is not None and rule.camera_id != camera_id:
        return False
    if rule.violation_type is not None and rule.violation_type != violation_type:
        return False
    return True


def _recent_event_exists(
    db: Session, camera_id: int, violation_type: str
) -> bool:
    since = datetime.now() - timedelta(minutes=EVENT_COOLDOWN_MINUTES)
    return (
        db.query(func.count(WarningEvent.id))
        .filter(
            WarningEvent.camera_id == camera_id,
            WarningEvent.violation_type == violation_type,
            WarningEvent.triggered_at >= since,
        )
        .scalar()
        or 0
    ) > 0


def _window_count(
    db: Session,
    camera_id: int,
    violation_type: str,
    window_minutes: int,
) -> int:
    """统计最近 window_minutes 分钟内该摄像头该类型的违规次数"""
    since = datetime.now() - timedelta(minutes=window_minutes)
    q = db.query(func.count(Violation.id)).filter(
        Violation.camera_id == camera_id,
        Violation.violation_type == violation_type,
        Violation.created_at >= since,
    )
    return q.scalar() or 0


def trigger_warning_check(
    db: Session, camera_id: int, camera_name: str, violation_type: str
):
    """违规入库后调用：命中规则则生成预警事件（幂等，静默窗口内不重复）。

    注意：必须在违规记录 commit 之后调用（统计需包含刚入库的记录）。
    """
    if _recent_event_exists(db, camera_id, violation_type):
        return
    rules = db.query(WarningRule).filter(WarningRule.enabled.is_(True)).all()
    for rule in rules:
        if not _rule_matches(rule, camera_id, violation_type):
            continue
        count = _window_count(
            db, camera_id, violation_type, rule.window_minutes
        )
        if count >= rule.threshold:
            db.add(
                WarningEvent(
                    rule_id=rule.id,
                    camera_id=camera_id,
                    camera_name=camera_name,
                    violation_type=violation_type,
                    count=count,
                )
            )
            db.commit()
            return
