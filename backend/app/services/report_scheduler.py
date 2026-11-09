"""日报 / 周报定时邮件推送

轻量后台线程：每 30 秒检查一次配置时间，到点且当天未发送则发送。
配置存于 `system_settings`（网页「预警配置 → 邮件与报告」可改）：
  report.daily_enabled / daily_time / weekly_enabled / weekly_day / weekly_time
  report.report_to / last_daily_sent / last_weekly_sent
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime

from ..database import SessionLocal
from .settings_service import (
    effective_report_recipients,
    get_mail_config,
    get_report_config,
    set_value,
)

logger = logging.getLogger(__name__)

_started = False


def _send_period(db, period: str) -> bool:
    """发送指定周期报告（daily/week）。返回是否成功。"""
    from ..routers.logs import REPORT_PERIOD_MAP, build_report_pdf
    from .mailer import send_custom_email

    days, period_name = REPORT_PERIOD_MAP[period]
    cfg = get_mail_config(db)
    cfg = {**cfg, "to": effective_report_recipients(db)}
    if not cfg.get("host") or not cfg.get("to"):
        logger.info("报告邮件未发送：未配置 SMTP 服务器或收件人")
        return False
    try:
        pdf, fname = build_report_pdf(db, days, period_name)
        subject = f"【智慧工地】安全{period_name}（{datetime.now().strftime('%Y-%m-%d')}）"
        html = (
            f"<p style='font-family:Microsoft YaHei,Arial;'>"
            f"附件为安全{period_name}，统计区间近 {days} 天，请查收。</p>"
        )
        ok = send_custom_email(
            cfg,
            subject,
            f"安全{period_name}见附件。",
            html,
            [(pdf, fname, "application/pdf")],
        )
        if ok:
            logger.info("定时报告已发送：%s", subject)
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.warning("定时报告发送异常：%s", exc)
        return False


def _time_reached(now: datetime, hhmm: str) -> bool:
    """当前时间是否已到达配置时刻（支持服务晚启动后的当天补发）。"""
    try:
        h, m = (int(x) for x in hhmm.split(":"))
    except (ValueError, AttributeError):
        return False
    return (now.hour, now.minute) >= (h, m)


def _tick() -> None:
    db = SessionLocal()
    try:
        rep = get_report_config(db)
        now = datetime.now()
        today = date.today().isoformat()

        if (
            rep["daily_enabled"]
            and rep["last_daily_sent"] != today
            and _time_reached(now, rep["daily_time"])
        ):
            if _send_period(db, "daily"):
                set_value(db, "report.last_daily_sent", today)

        if (
            rep["weekly_enabled"]
            and int(rep["weekly_day"]) == now.isoweekday()
            and rep["last_weekly_sent"] != today
            and _time_reached(now, rep["weekly_time"])
        ):
            if _send_period(db, "week"):
                set_value(db, "report.last_weekly_sent", today)
    except Exception as exc:  # noqa: BLE001
        logger.warning("报告调度检查异常：%s", exc)
    finally:
        db.close()


def _loop() -> None:
    logger.info("报告定时调度已启动（每 30 秒检查一次）")
    while True:
        _tick()
        time.sleep(30)


def start_report_scheduler() -> None:
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, name="report-scheduler", daemon=True).start()
