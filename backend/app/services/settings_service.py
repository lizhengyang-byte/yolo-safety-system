"""系统配置服务：邮件 SMTP / 报告推送配置（数据库持久化，网页可改）

配置优先级：数据库 system_settings 中存在该键 → 使用数据库值；否则回退到
环境变量 / config.Settings 的默认值。因此既支持网页配置，也兼容原有 .env 配置。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import settings
from ..models import SystemSetting

# ---------- 默认值（来自环境变量 / config.Settings） ----------
MAIL_KEY_MAP = {
    "enabled": "mail.enabled",
    "host": "mail.host",
    "port": "mail.port",
    "user": "mail.user",
    "password": "mail.password",
    "ssl": "mail.ssl",
    "starttls": "mail.starttls",
    "from": "mail.from",
    "to": "mail.to",
}

REPORT_KEY_MAP = {
    "warning_email_enabled": "report.warning_email_enabled",
    "daily_enabled": "report.daily_enabled",
    "daily_time": "report.daily_time",
    "weekly_enabled": "report.weekly_enabled",
    "weekly_day": "report.weekly_day",
    "weekly_time": "report.weekly_time",
    "report_to": "report.report_to",
    "last_daily_sent": "report.last_daily_sent",
    "last_weekly_sent": "report.last_weekly_sent",
}


def _as_bool(v, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on", "是")


def _as_int(v, default: int = 0) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def _all(db: Session) -> dict[str, str]:
    return {row.key: (row.value or "") for row in db.query(SystemSetting).all()}


def _pick(raw: dict[str, str], key: str, default):
    return raw[key] if key in raw else default


# ---------- 邮件配置 ----------
def get_mail_config(db: Session) -> dict:
    """返回完整邮件配置（含真实密码，供发送使用；接口返回时需脱敏）。"""
    raw = _all(db)
    return {
        "enabled": _as_bool(_pick(raw, "mail.enabled", settings.MAIL_ENABLED)),
        "host": str(_pick(raw, "mail.host", settings.SMTP_HOST) or "").strip(),
        "port": _as_int(_pick(raw, "mail.port", settings.SMTP_PORT), settings.SMTP_PORT),
        "user": str(_pick(raw, "mail.user", settings.SMTP_USER) or "").strip(),
        "password": str(_pick(raw, "mail.password", settings.SMTP_PASSWORD) or ""),
        "ssl": _as_bool(_pick(raw, "mail.ssl", settings.SMTP_SSL)),
        "starttls": _as_bool(_pick(raw, "mail.starttls", settings.SMTP_STARTTLS)),
        "from": str(_pick(raw, "mail.from", settings.MAIL_FROM) or "").strip(),
        "to": str(_pick(raw, "mail.to", settings.MAIL_TO) or "").strip(),
    }


def save_mail_config(db: Session, data: dict) -> dict:
    """保存邮件配置；password 为掩码/空时保留原密码。"""
    current = get_mail_config(db)
    values = {
        "mail.enabled": str(bool(data.get("enabled", current["enabled"]))).lower(),
        "mail.host": str(data.get("host", current["host"]) or "").strip(),
        "mail.port": str(_as_int(data.get("port", current["port"]), current["port"])),
        "mail.user": str(data.get("user", current["user"]) or "").strip(),
        "mail.ssl": str(bool(data.get("ssl", current["ssl"]))).lower(),
        "mail.starttls": str(bool(data.get("starttls", current["starttls"]))).lower(),
        "mail.from": str(data.get("from", current["from"]) or "").strip(),
        "mail.to": str(data.get("to", current["to"]) or "").strip(),
    }
    pwd = data.get("password")
    if pwd not in (None, "", "******", "********"):
        values["mail.password"] = str(pwd)
    _upsert(db, values)
    return get_mail_config(db)


# ---------- 报告推送配置 ----------
def get_report_config(db: Session) -> dict:
    raw = _all(db)
    return {
        "warning_email_enabled": _as_bool(
            _pick(raw, "report.warning_email_enabled", True), True
        ),
        "daily_enabled": _as_bool(_pick(raw, "report.daily_enabled", False)),
        "daily_time": str(_pick(raw, "report.daily_time", "08:30") or "08:30"),
        "weekly_enabled": _as_bool(_pick(raw, "report.weekly_enabled", False)),
        "weekly_day": _as_int(_pick(raw, "report.weekly_day", 1), 1),
        "weekly_time": str(_pick(raw, "report.weekly_time", "09:00") or "09:00"),
        "report_to": str(_pick(raw, "report.report_to", "") or "").strip(),
        "last_daily_sent": str(_pick(raw, "report.last_daily_sent", "") or ""),
        "last_weekly_sent": str(_pick(raw, "report.last_weekly_sent", "") or ""),
    }


def save_report_config(db: Session, data: dict) -> dict:
    current = get_report_config(db)
    values = {
        "report.warning_email_enabled": str(
            bool(data.get("warning_email_enabled", current["warning_email_enabled"]))
        ).lower(),
        "report.daily_enabled": str(
            bool(data.get("daily_enabled", current["daily_enabled"]))
        ).lower(),
        "report.daily_time": str(data.get("daily_time", current["daily_time"]) or "08:30"),
        "report.weekly_enabled": str(
            bool(data.get("weekly_enabled", current["weekly_enabled"]))
        ).lower(),
        "report.weekly_day": str(
            _as_int(data.get("weekly_day", current["weekly_day"]), current["weekly_day"])
        ),
        "report.weekly_time": str(
            data.get("weekly_time", current["weekly_time"]) or "09:00"
        ),
        "report.report_to": str(data.get("report_to", current["report_to"]) or "").strip(),
    }
    _upsert(db, values)
    return get_report_config(db)


def set_value(db: Session, key: str, value: str, commit: bool = True) -> None:
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=str(value)))
    else:
        row.value = str(value)
    if commit:
        db.commit()


def _upsert(db: Session, values: dict[str, str]) -> None:
    for key, value in values.items():
        row = db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()


def effective_report_recipients(db: Session) -> str:
    """报告收件人：未单独配置时回退到邮件收件人。"""
    mail = get_mail_config(db)
    report = get_report_config(db)
    return report["report_to"] or mail["to"]
