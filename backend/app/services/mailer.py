"""邮件发送（SMTP）

配置来自数据库 `system_settings`（网页可改），缺省回退到 config.Settings / .env：
  MAIL_ENABLED / SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD /
  SMTP_SSL / SMTP_STARTTLS / MAIL_FROM / MAIL_TO

未配置 host / to 时静默跳过，不影响系统运行。发送均在后台线程执行。
"""
from __future__ import annotations

import logging
import mimetypes
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate

logger = logging.getLogger(__name__)


def recipients(cfg: dict) -> list[str]:
    raw = (cfg.get("to") or "").replace(";", ",")
    return [x.strip() for x in raw.split(",") if x.strip()]


def is_configured(cfg: dict) -> bool:
    return bool(cfg.get("enabled", True) and cfg.get("host") and cfg.get("to"))


def _from_addr(cfg: dict) -> str:
    return cfg.get("from") or cfg.get("user") or "noreply@localhost"


def _send(cfg: dict, msg: EmailMessage) -> bool:
    if not is_configured(cfg):
        logger.info("邮件未配置（host / to 为空），跳过发送")
        return False
    try:
        if cfg.get("ssl"):
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                cfg["host"], int(cfg.get("port") or 465), timeout=15
            )
        else:
            server = smtplib.SMTP(
                cfg["host"], int(cfg.get("port") or 25), timeout=15
            )
        with server:
            if cfg.get("starttls") and not cfg.get("ssl"):
                server.starttls()
            if cfg.get("user"):
                server.login(cfg["user"], cfg.get("password") or "")
            server.send_message(msg)
        logger.info("邮件已发送：%s -> %s", msg["Subject"], recipients(cfg))
        return True
    except Exception as exc:  # noqa: BLE001 - 邮件失败不能影响主流程
        logger.warning("邮件发送失败：%s", exc)
        return False


def _attach(msg: EmailMessage, attachments: list[tuple[bytes, str, str]] | None):
    for content, filename, mime in attachments or []:
        maintype, _, subtype = (mime or "application/octet-stream").partition("/")
        msg.add_attachment(
            content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=filename,
        )


def send_custom_email(
    cfg: dict,
    subject: str,
    text: str,
    html: str | None = None,
    attachments: list[tuple[bytes, str, str]] | None = None,
) -> bool:
    """通用发送：HTML + 若干附件（bytes, filename, mime）。"""
    if not is_configured(cfg):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("智慧工地安全监测", _from_addr(cfg)))
    msg["To"] = ", ".join(recipients(cfg))
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    _attach(msg, attachments)
    return _send(cfg, msg)


def _warning_html(payload: dict) -> str:
    type_label = payload.get("type_label") or payload.get("violation_type") or "违规"
    camera = payload.get("camera_name") or "未知摄像头"
    location = payload.get("location") or "-"
    count = payload.get("count", 0)
    triggered_at = payload.get("triggered_at") or datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = "".join(
        f"<tr><td style='padding:6px 12px;color:#64748b'>{k}</td>"
        f"<td style='padding:6px 12px;color:#0f172a;font-weight:600'>{v}</td></tr>"
        for k, v in [
            ("摄像头", camera),
            ("点位", location),
            ("违规类型", type_label),
            ("窗口内次数", count),
            ("触发时间", triggered_at),
        ]
    )
    return f"""
    <div style="font-family:'Microsoft YaHei',Arial,sans-serif;max-width:560px">
      <div style="background:linear-gradient(135deg,#2f6bff,#22d3ee);color:#fff;
                  padding:16px 20px;border-radius:10px 10px 0 0">
        <div style="font-size:18px;font-weight:700">⚠ 智慧工地安全预警</div>
        <div style="font-size:12px;opacity:.85;margin-top:4px">AI 安全监测系统自动通知</div>
      </div>
      <table style="width:100%;border-collapse:collapse;background:#f8fafc;
                    border:1px solid #e2e8f0;border-top:none">{rows}</table>
      <div style="padding:12px 20px;font-size:12px;color:#94a3b8">
        抓拍证据图见邮件附件；请及时登录后台处理。
      </div>
    </div>
    """


def send_warning_email(payload: dict, image_path: str | None, cfg: dict) -> bool:
    """发送预警邮件（正文 + 抓拍图附件）。"""
    if not is_configured(cfg):
        logger.info("邮件未配置（host / to 为空），跳过预警邮件")
        return False

    type_label = payload.get("type_label") or payload.get("violation_type") or "违规"
    camera = payload.get("camera_name") or "未知摄像头"
    count = payload.get("count", 0)
    triggered_at = payload.get("triggered_at") or ""
    subject = f"【智慧工地预警】{type_label} · {camera} · 窗口内 {count} 次"
    text = "\n".join(
        [
            "智慧工地 AI 安全监测系统 预警通知",
            "--------------------------------",
            f"摄像头：{camera}",
            f"点位：{payload.get('location') or '-'}",
            f"违规类型：{type_label}",
            f"窗口内次数：{count}",
            f"触发时间：{triggered_at}",
        ]
    )

    attachments: list[tuple[bytes, str, str]] = []
    if image_path and os.path.exists(image_path):
        ctype, _ = mimetypes.guess_type(image_path)
        try:
            with open(image_path, "rb") as f:
                attachments.append(
                    (f.read(), os.path.basename(image_path), ctype or "image/jpeg")
                )
        except OSError as exc:
            logger.warning("邮件附件读取失败：%s", exc)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("智慧工地安全监测", _from_addr(cfg)))
    msg["To"] = ", ".join(recipients(cfg))
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text)
    msg.add_alternative(_warning_html(payload), subtype="html")
    _attach(msg, attachments)
    return _send(cfg, msg)


def send_test_email(cfg: dict) -> tuple[bool, str]:
    if not is_configured(cfg):
        return False, "未配置 SMTP 服务器或收件人，请先在页面填写并保存"
    payload = {
        "violation_type": "test",
        "type_label": "测试邮件",
        "camera_name": "系统自检",
        "location": "-",
        "count": 0,
        "triggered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    ok = send_warning_email(payload, None, cfg)
    return ok, "测试邮件已发送，请查收" if ok else "测试邮件发送失败，请检查 SMTP 配置或后端日志"
