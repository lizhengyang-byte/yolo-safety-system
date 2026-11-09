"""预警中心：预警规则管理 + 预警事件查询/已读

规则在违规入库时由 services/warnings.py 自动触发检查（见 violations.py / demo.py）。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WarningEvent, WarningRule
from ..schemas import (
    MessageOut,
    WarningEventOut,
    WarningEventPage,
    WarningRuleCreate,
    WarningRuleOut,
    WarningRuleUpdate,
)

router = APIRouter()


# ---------- 规则 CRUD ----------
@router.get("/rules", response_model=List[WarningRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return (
        db.query(WarningRule)
        .order_by(WarningRule.id.desc())
        .all()
    )


@router.post("/rules", response_model=WarningRuleOut, status_code=201)
def create_rule(body: WarningRuleCreate, db: Session = Depends(get_db)):
    rule = WarningRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=WarningRuleOut)
def update_rule(rule_id: int, body: WarningRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(WarningRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", response_model=WarningRuleOut)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(WarningRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()
    return rule


# ---------- 预警事件 ----------
@router.get("/events", response_model=WarningEventPage)
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(WarningEvent)
    if unread_only:
        q = q.filter(WarningEvent.is_read.is_(False))
    total = q.count()
    items = (
        q.order_by(WarningEvent.triggered_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return WarningEventPage(total=total, items=items)


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db)):
    """未读预警事件数（顶栏铃铛徽标轮询）"""
    n = (
        db.query(WarningEvent.id)
        .filter(WarningEvent.is_read.is_(False))
        .count()
    )
    return {"count": n}


@router.post("/events/read", response_model=MessageOut)
def mark_read(
    ids: List[int] = Query(...), db: Session = Depends(get_db)
):
    """按 ID 列表标记已读"""
    db.query(WarningEvent).filter(
        WarningEvent.id.in_(ids)
    ).update({WarningEvent.is_read: True}, synchronize_session=False)
    db.commit()
    return {"message": f"已标记 {len(ids)} 条为已读"}


@router.post("/events/read-all", response_model=MessageOut)
def mark_all_read(db: Session = Depends(get_db)):
    """全部标记已读"""
    n = (
        db.query(WarningEvent)
        .filter(WarningEvent.is_read.is_(False))
        .update({WarningEvent.is_read: True}, synchronize_session=False)
    )
    db.commit()
    return {"message": f"已全部标记为已读（{n} 条）"}


@router.post("/email/test")
def email_test(db: Session = Depends(get_db)):
    """发送测试邮件，用于验证 SMTP 配置（未配置会返回提示）。"""
    from ..services.mailer import send_test_email
    from ..services.settings_service import get_mail_config

    ok, message = send_test_email(get_mail_config(db))
    return {"ok": ok, "message": message}
