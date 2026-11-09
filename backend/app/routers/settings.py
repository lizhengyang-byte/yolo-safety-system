"""系统配置：邮件 SMTP / 报告推送配置（网页端在线修改）"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.mailer import send_test_email
from ..services.settings_service import (
    effective_report_recipients,
    get_mail_config,
    get_report_config,
    save_mail_config,
    save_report_config,
)

router = APIRouter()


class MailConfigPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: Optional[bool] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    ssl: Optional[bool] = None
    starttls: Optional[bool] = None
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None


class ReportConfigPayload(BaseModel):
    warning_email_enabled: Optional[bool] = None
    daily_enabled: Optional[bool] = None
    daily_time: Optional[str] = None
    weekly_enabled: Optional[bool] = None
    weekly_day: Optional[int] = None
    weekly_time: Optional[str] = None
    report_to: Optional[str] = None


def _mask_mail(cfg: dict) -> dict:
    return {
        **cfg,
        "password": "******" if cfg.get("password") else "",
        "has_password": bool(cfg.get("password")),
    }


@router.get("/mail")
def get_mail(db: Session = Depends(get_db)):
    return _mask_mail(get_mail_config(db))


@router.put("/mail")
def update_mail(body: MailConfigPayload, db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    # 兼容前端字段 from（Pydantic 用 from_ 接收）
    if "from_" in data:
        data["from"] = data.pop("from_")
    return _mask_mail(save_mail_config(db, data))


@router.post("/mail/test")
def test_mail(db: Session = Depends(get_db)):
    ok, message = send_test_email(get_mail_config(db))
    return {"ok": ok, "message": message}


@router.get("/report")
def get_report(db: Session = Depends(get_db)):
    cfg = get_report_config(db)
    cfg["effective_to"] = effective_report_recipients(db)
    return cfg


@router.put("/report")
def update_report(body: ReportConfigPayload, db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    cfg = save_report_config(db, data)
    cfg["effective_to"] = effective_report_recipients(db)
    return cfg


@router.post("/report/send")
def send_report_now(
    period: str = Query("week", pattern="^(daily|week|month)$"),
    db: Session = Depends(get_db),
):
    """立即生成并发送报告邮件（日报/周报/月报）。"""
    from ..services.report_scheduler import _send_period

    cfg = get_mail_config(db)
    to = effective_report_recipients(db)
    if not cfg.get("host") or not to:
        raise HTTPException(
            status_code=400,
            detail="未配置 SMTP 服务器或收件人，请先在上方填写并保存",
        )
    ok = _send_period(db, period)
    if not ok:
        raise HTTPException(
            status_code=500, detail="发送失败，请检查 SMTP 配置或后端日志"
        )
    return {"message": f"报告已发送至 {to}"}
