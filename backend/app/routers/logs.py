"""安全日志：统计 + 数据看板聚合 + Excel/PDF 导出（Excel 含违规图片）"""
import io
import os
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..detection.annotate import VIOLATION_LABELS
from ..models import Camera, Violation, WarningEvent

router = APIRouter()

# Excel 行数上限（避免一次性导出全量导致内存/体积失控）
EXPORT_ROW_LIMIT = 5000


def _build_query(
    db: Session,
    violation_type: Optional[str] = None,
    camera_id: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    """列表与导出共用的筛选条件构建"""
    q = db.query(Violation)
    if violation_type:
        q = q.filter(Violation.violation_type == violation_type)
    if camera_id:
        q = q.filter(Violation.camera_id == camera_id)
    if start:
        q = q.filter(Violation.created_at >= f"{start} 00:00:00")
    if end:
        q = q.filter(Violation.created_at <= f"{end} 23:59:59")
    return q


def _resolve_image_file(v: Violation) -> Optional[str]:
    """把记录里的 image_path / image_url 解析为服务器本地文件路径"""
    if v.image_path and os.path.exists(v.image_path):
        return v.image_path
    base = settings.UPLOAD_DIR
    if v.image_url:
        p = os.path.join(base, os.path.basename(v.image_url))
        if os.path.exists(p):
            return p
    if v.image_path:
        p = os.path.join(base, os.path.basename(v.image_path))
        if os.path.exists(p):
            return p
    return None


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """各违规类型数量统计，供首页/看板使用"""
    rows = (
        db.query(Violation.violation_type, func.count(Violation.id))
        .group_by(Violation.violation_type)
        .all()
    )
    total = db.query(func.count(Violation.id)).scalar() or 0
    return {
        "total": total,
        "detail": [{"type": t, "count": c} for t, c in rows],
    }


@router.get("/dashboard")
def dashboard(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    """数据看板聚合接口（管理台 + 智慧大屏共用）。

    基础字段（保持向后兼容）：总数 / 今日 / 在线摄像头 / 近N天趋势 / 类型分布 /
    摄像头排行 / 点位排行。

    大屏增强字段（仅追加，不改旧字段）：
      - deltas：今日与上一日、本窗口与上一窗口的环比
      - hourly：今日 0-23 时违规分布（24 点）
      - avg_confidence：窗口内平均识别置信度（0~1）
      - latest：最新 6 条违规（含图片 / 点位 / 置信度）
      - camera_status：摄像头在线状态 + 窗口内违规数
      - warning_summary：未读 / 今日预警数 + 最新 5 条预警事件

    days：趋势与分布类统计的窗口天数（默认 7，前端可切换 30 / 90 查看长期趋势）。
    """
    total = db.query(func.count(Violation.id)).scalar() or 0
    today = (
        db.query(func.count(Violation.id))
        .filter(func.date(Violation.created_at) == date.today())
        .scalar()
        or 0
    )
    online = (
        db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0
    )

    # 统计窗口起点（含当天共 days 天）
    start_dt = datetime.combine(
        date.today() - timedelta(days=days - 1), datetime.min.time()
    )

    # 近 N 天趋势（含 0 天）
    day_rows = (
        db.query(func.date(Violation.created_at).label("d"), func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .group_by(func.date(Violation.created_at))
        .all()
    )
    day_map = {str(d): c for d, c in day_rows}
    trend = []
    for i in range(days - 1, -1, -1):
        d = date.today() - timedelta(days=i)
        trend.append({"date": d.isoformat(), "count": day_map.get(d.isoformat(), 0)})

    # 窗口内类型分布
    type_rows = (
        db.query(Violation.violation_type, func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .group_by(Violation.violation_type)
        .order_by(func.count(Violation.id).desc())
        .all()
    )
    types = [{"type": t, "count": c} for t, c in type_rows]

    # 窗口内摄像头违规排行
    cam_rows = (
        db.query(Violation.camera_name, func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .group_by(Violation.camera_name)
        .order_by(func.count(Violation.id).desc())
        .limit(10)
        .all()
    )
    ranking = [{"name": n or "未知", "count": c} for n, c in cam_rows]

    # 窗口内点位（安装位置）违规排行：violations LEFT JOIN cameras 取 location
    loc_rows = (
        db.query(
            func.coalesce(Camera.location, "").label("loc"),
            func.count(Violation.id),
        )
        .filter(Violation.created_at >= start_dt)
        .outerjoin(Camera, Violation.camera_id == Camera.id)
        .group_by(func.coalesce(Camera.location, ""))
        .order_by(func.count(Violation.id).desc())
        .limit(8)
        .all()
    )
    location_ranking = [
        {"location": loc or "未填点位", "count": c} for loc, c in loc_rows
    ]

    # ---- 大屏增强字段（只追加，不改旧字段）----
    window_total = sum(p["count"] for p in trend)

    # 上一统计窗口（紧邻 start_dt 之前的 days 天）
    prev_start = start_dt - timedelta(days=days)
    prev_total = (
        db.query(func.count(Violation.id))
        .filter(Violation.created_at >= prev_start)
        .filter(Violation.created_at < start_dt)
        .scalar()
        or 0
    )
    # 上一日（昨日）违规数
    yesterday = date.today() - timedelta(days=1)
    today_prev = (
        db.query(func.count(Violation.id))
        .filter(func.date(Violation.created_at) == yesterday)
        .scalar()
        or 0
    )
    growth_pct = (
        round((window_total - prev_total) * 100.0 / prev_total, 1) if prev_total else None
    )
    deltas = {
        "today_prev": today_prev,
        "today_delta": today - today_prev,
        "week_prev": prev_total,
        "week_delta": window_total - prev_total,
        "growth_pct": growth_pct,
    }

    # 今日 0-23 时分布（Python 侧分桶，避免 SQLite/MySQL 方言差异）
    today_start = datetime.combine(date.today(), datetime.min.time())
    hour_rows = (
        db.query(Violation.created_at)
        .filter(Violation.created_at >= today_start)
        .all()
    )
    hour_counts = [0] * 24
    for (ts,) in hour_rows:
        if ts is not None and 0 <= ts.hour < 24:
            hour_counts[ts.hour] += 1
    hourly = [{"hour": h, "count": hour_counts[h]} for h in range(24)]

    # 窗口内平均置信度
    avg_conf = (
        db.query(func.avg(Violation.confidence))
        .filter(Violation.created_at >= start_dt)
        .scalar()
    )
    avg_confidence = round(float(avg_conf), 3) if avg_conf is not None else 0.0

    # 最新 6 条违规（含点位）
    latest_rows = (
        db.query(Violation, Camera.location)
        .outerjoin(Camera, Violation.camera_id == Camera.id)
        .order_by(Violation.created_at.desc())
        .limit(6)
        .all()
    )
    latest = [
        {
            "id": v.id,
            "camera_id": v.camera_id,
            "camera_name": v.camera_name or "未知",
            "location": loc or "",
            "violation_type": v.violation_type,
            "confidence": round(float(v.confidence or 0), 3),
            "image_url": v.image_url or "",
            "anno_url": v.anno_url or "",
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if v.created_at
            else "",
        }
        for v, loc in latest_rows
    ]

    # 摄像头在线状态 + 窗口内违规数
    cameras = db.query(Camera).order_by(Camera.id).all()
    cam_count_rows = (
        db.query(Violation.camera_id, func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .group_by(Violation.camera_id)
        .all()
    )
    cam_count_map = {cid: c for cid, c in cam_count_rows}
    camera_status = [
        {
            "id": c.id,
            "name": c.name,
            "location": c.location or "",
            "status": c.status or "offline",
            "enabled": bool(c.enabled),
            "recent_count": cam_count_map.get(c.id, 0),
        }
        for c in cameras
    ]

    # 预警摘要（未读 / 今日 / 最新 5 条）
    unread = (
        db.query(func.count(WarningEvent.id))
        .filter(WarningEvent.is_read == False)  # noqa: E712
        .scalar()
        or 0
    )
    warn_today = (
        db.query(func.count(WarningEvent.id))
        .filter(func.date(WarningEvent.triggered_at) == date.today())
        .scalar()
        or 0
    )
    warn_rows = (
        db.query(WarningEvent).order_by(WarningEvent.triggered_at.desc()).limit(5).all()
    )
    warning_summary = {
        "unread": unread,
        "today": warn_today,
        "latest": [
            {
                "id": w.id,
                "camera_name": w.camera_name or "未知",
                "violation_type": w.violation_type,
                "count": w.count,
                "is_read": bool(w.is_read),
                "triggered_at": w.triggered_at.strftime("%Y-%m-%d %H:%M:%S")
                if w.triggered_at
                else "",
            }
            for w in warn_rows
        ],
    }

    return {
        "total": total,
        "today": today,
        "online_cameras": online,
        "trend": trend,
        "types": types,
        "ranking": ranking,
        "location_ranking": location_ranking,
        "deltas": deltas,
        "hourly": hourly,
        "avg_confidence": avg_confidence,
        "latest": latest,
        "camera_status": camera_status,
        "warning_summary": warning_summary,
    }


@router.get("/export")
def export_excel(
    violation_type: str = Query(None),
    camera_id: int = Query(None),
    start: str = Query(None),
    end: str = Query(None),
    db: Session = Depends(get_db),
):
    """导出安全日志为 Excel（筛选条件与列表一致，含违规图片缩略图）。

    无 pandas/openpyxl 时回退 CSV。
    """
    rows = (
        _build_query(db, violation_type, camera_id, start, end)
        .order_by(Violation.created_at.desc())
        .limit(EXPORT_ROW_LIMIT)
        .all()
    )

    def _row_to_dict(v: Violation) -> dict:
        return {
            "ID": v.id,
            "摄像头": v.camera_name,
            "违规类型": v.violation_type,
            "置信度": round(v.confidence or 0, 3),
            "抓拍时间": v.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if v.created_at
            else "",
            "图片": "",
        }

    try:
        import pandas as pd

        data = [_row_to_dict(v) for v in rows]
        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="安全日志")

        # 在 Excel 中嵌入违规图片缩略图
        from openpyxl import load_workbook
        from openpyxl.drawing.image import Image as XLImage
        from openpyxl.utils import get_column_letter

        wb = load_workbook(io.BytesIO(buffer.getvalue()))
        ws = wb.active
        header = [c.value for c in ws[1]]
        img_col = header.index("图片") + 1 if "图片" in header else None
        if img_col:
            ws.column_dimensions[get_column_letter(img_col)].width = 18
            for i, v in enumerate(rows, start=2):
                path = _resolve_image_file(v)
                if not path:
                    continue
                try:
                    xl = XLImage(path)
                    xl.width, xl.height = 120, 75
                    ws.add_image(xl, f"{get_column_letter(img_col)}{i}")
                    ws.row_dimensions[i].height = 80
                except Exception:
                    continue
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)

        fname = f"安全日志_{start or '全部'}_{end or '至今'}.xlsx"
        return StreamingResponse(
            out,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; filename=safety_logs.xlsx; "
                    f"filename*=UTF-8''{quote(fname)}"
                )
            },
        )
    except Exception:
        # 无 pandas 时返回 CSV 兜底
        import csv

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "摄像头", "违规类型", "置信度", "抓拍时间", "图片地址"])
        for v in rows:
            writer.writerow(
                [
                    v.id,
                    v.camera_name,
                    v.violation_type,
                    round(v.confidence or 0, 3),
                    v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else "",
                    v.image_url,
                ]
            )
        buf.seek(0)
        fname = f"安全日志_{start or '全部'}_{end or '至今'}.csv"
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=safety_logs.csv; "
                    f"filename*=UTF-8''{quote(fname)}"
                )
            },
        )


# ---------- PDF 安全报告导出（周报 / 月报） ----------
_PDF_FONT = "STSong-Light"
_pdf_fonts_ready = False


def _ensure_pdf_fonts():
    """注册 reportlab 内置中文字体（STSong-Light CID 字体，无需外部字体文件）。

    Windows 与 Docker（python:3.12-slim）均可直接用，避免依赖系统中文字体。
    """
    global _pdf_fonts_ready
    if _pdf_fonts_ready:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    pdfmetrics.registerFont(UnicodeCIDFont(_PDF_FONT))
    _pdf_fonts_ready = True


def _pdf_table_style():
    """PDF 表格统一样式：表头深蓝底白字 + 细网格"""
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import TableStyle

    style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), _PDF_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#dcdfe6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1f3b73")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ]
    )
    return style


def _build_trend_chart(trend: list):
    """手绘折线趋势图（shapes 原语，不依赖 charts 组件——reportlab 4.2 重构后
    LineChart 经典 data API 已变更，手绘最稳定且 7/30 天标签密度自适应）"""
    from reportlab.graphics.shapes import (
        Circle,
        Drawing,
        Line,
        PolyLine,
        String,
    )
    from reportlab.lib.colors import HexColor

    n = len(trend)
    counts = [p["count"] for p in trend]
    maxc = max(counts) or 1

    left, bottom, width, height = 52, 36, 390, 128
    drawing = Drawing(470, 190)

    # 水平网格线 + Y 轴刻度（4 等分）
    for i in range(5):
        y = bottom + height * i / 4
        drawing.add(
            Line(left, y, left + width, y, strokeColor=HexColor("#ebeef5"), strokeWidth=0.5)
        )
        drawing.add(
            String(left - 10, y - 3, str(round(maxc * i / 4)), fontSize=7)
        )
    # 坐标轴
    drawing.add(
        Line(left, bottom, left + width, bottom, strokeColor=HexColor("#909399"), strokeWidth=0.8)
    )
    drawing.add(
        Line(left, bottom, left, bottom + height, strokeColor=HexColor("#909399"), strokeWidth=0.8)
    )

    # 折线 + 数据点
    pts = []
    step_x = width / max(1, n - 1)
    for i, c in enumerate(counts):
        x = left + step_x * i
        y = bottom + height * c / maxc
        pts.append((x, y))
        drawing.add(Circle(x, y, 1.6, fillColor=HexColor("#f56c6c")))
    drawing.add(
        PolyLine(pts, strokeColor=HexColor("#f56c6c"), strokeWidth=1.6)
    )

    # X 轴日期标签（间隔显示，避免 30 天标签重叠）
    step = max(1, n // 8)
    for i, p in enumerate(trend):
        if i % step == 0 or i == n - 1:
            x = left + step_x * i
            label = String(x, bottom - 14, p["date"][5:], fontSize=7)
            label.textAnchor = "middle"
            drawing.add(label)

    return drawing


@router.get("/report")
def export_report(period: str = Query("week", pattern="^(week|month)$"), db: Session = Depends(get_db)):
    """导出安全报告 PDF：周报（近 7 天）/ 月报（近 30 天）。

    内容：统计摘要（期间违规总数/日均/今日/在线摄像头）、违规趋势图、
    类型分布、点位排行、违规明细（前 50 条）。
    """
    try:
        import reportlab  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="reportlab 未安装，无法生成 PDF 报告",
        )
    _ensure_pdf_fonts()

    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    days = 7 if period == "week" else 30
    period_name = "周报" if period == "week" else "月报"
    start_dt = datetime.combine(
        date.today() - timedelta(days=days - 1), datetime.min.time()
    )

    total = (
        db.query(func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .scalar()
        or 0
    )
    today_n = (
        db.query(func.count(Violation.id))
        .filter(func.date(Violation.created_at) == date.today())
        .scalar()
        or 0
    )
    online = (
        db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0
    )
    avg_per_day = round(total / days, 1)

    # 趋势
    day_rows = (
        db.query(func.date(Violation.created_at).label("d"), func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .group_by(func.date(Violation.created_at))
        .all()
    )
    day_map = {str(d): c for d, c in day_rows}
    trend = []
    for i in range(days - 1, -1, -1):
        d = date.today() - timedelta(days=i)
        trend.append({"date": d.isoformat(), "count": day_map.get(d.isoformat(), 0)})

    # 类型分布（窗口内）
    type_rows = (
        db.query(Violation.violation_type, func.count(Violation.id))
        .filter(Violation.created_at >= start_dt)
        .group_by(Violation.violation_type)
        .order_by(func.count(Violation.id).desc())
        .all()
    )
    # 点位排行（窗口内）
    loc_rows = (
        db.query(
            func.coalesce(Camera.location, "").label("loc"),
            func.count(Violation.id),
        )
        .filter(Violation.created_at >= start_dt)
        .outerjoin(Camera, Violation.camera_id == Camera.id)
        .group_by(func.coalesce(Camera.location, ""))
        .order_by(func.count(Violation.id).desc())
        .limit(8)
        .all()
    )
    # 明细（前 50 条）
    details = (
        db.query(Violation)
        .filter(Violation.created_at >= start_dt)
        .order_by(Violation.created_at.desc())
        .limit(50)
        .all()
    )

    # ---------- 构建 PDF ----------
    title_style = ParagraphStyle(
        "title", fontName=_PDF_FONT, fontSize=20, leading=28, alignment=TA_CENTER
    )
    sub_style = ParagraphStyle(
        "sub",
        fontName=_PDF_FONT,
        fontSize=10,
        leading=16,
        alignment=TA_CENTER,
        textColor=HexColor("#888888"),
    )
    h2_style = ParagraphStyle(
        "h2",
        fontName=_PDF_FONT,
        fontSize=14,
        leading=20,
        spaceBefore=16,
        spaceAfter=6,
        textColor=HexColor("#1f3b73"),
    )
    cell = ParagraphStyle("cell", fontName=_PDF_FONT, fontSize=9.5, leading=14)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
    )
    story = [
        Paragraph(f"工地AI安全智能监测系统 — 安全{period_name}", title_style),
        Paragraph(
            f"统计区间：{trend[0]['date']} ~ {trend[-1]['date']}　|　"
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            sub_style,
        ),
        Spacer(1, 8),
    ]

    # 统计摘要
    summary = Table(
        [
            [
                Paragraph(f"<b>{total}</b>", cell),
                Paragraph(f"<b>{avg_per_day}</b>", cell),
                Paragraph(f"<b>{today_n}</b>", cell),
                Paragraph(f"<b>{online}</b>", cell),
            ],
            [
                Paragraph("期间违规总数", cell),
                Paragraph("日均违规", cell),
                Paragraph("今日违规", cell),
                Paragraph("在线摄像头", cell),
            ],
        ],
        colWidths=[42 * mm] * 4,
    )
    summary.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), _PDF_FONT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f5f7fa")),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dcdfe6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(summary)

    # 趋势图
    story.append(Paragraph("违规趋势（按天）", h2_style))
    story.append(_build_trend_chart(trend))

    # 类型分布 + 点位排行
    story.append(Paragraph("违规类型分布", h2_style))
    type_total = sum(c for _, c in type_rows) or 1
    tdata = [
        [Paragraph("违规类型", cell), Paragraph("数量", cell), Paragraph("占比", cell)]
    ]
    if type_rows:
        for t, c in type_rows:
            tdata.append(
                [
                    Paragraph(VIOLATION_LABELS.get(t, t), cell),
                    Paragraph(str(c), cell),
                    Paragraph(f"{c / type_total * 100:.1f}%", cell),
                ]
            )
    else:
        tdata.append([Paragraph("（窗口内暂无违规记录）", cell), "", ""])
    ttable = Table(tdata, colWidths=[90 * mm, 30 * mm, 30 * mm])
    ttable.setStyle(_pdf_table_style())
    story.append(ttable)

    story.append(Paragraph("点位违规排行", h2_style))
    loc_total = sum(c for _, c in loc_rows) or 1
    ldata = [
        [Paragraph("点位", cell), Paragraph("违规数", cell), Paragraph("占比", cell)]
    ]
    if loc_rows:
        for loc, c in loc_rows:
            ldata.append(
                [
                    Paragraph(loc or "未填点位", cell),
                    Paragraph(str(c), cell),
                    Paragraph(f"{c / loc_total * 100:.1f}%", cell),
                ]
            )
    else:
        ldata.append([Paragraph("（窗口内暂无违规记录）", cell), "", ""])
    ltable = Table(ldata, colWidths=[90 * mm, 30 * mm, 30 * mm])
    ltable.setStyle(_pdf_table_style())
    story.append(ltable)

    # 违规明细
    story.append(Paragraph(f"期间违规明细（前 {len(details)} 条）", h2_style))
    ddata = [
        [
            Paragraph("抓拍时间", cell),
            Paragraph("摄像头", cell),
            Paragraph("违规类型", cell),
            Paragraph("置信度", cell),
        ]
    ]
    for v in details:
        ddata.append(
            [
                Paragraph(
                    v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else "",
                    cell,
                ),
                Paragraph(v.camera_name or "未知", cell),
                Paragraph(VIOLATION_LABELS.get(v.violation_type, v.violation_type), cell),
                Paragraph(f"{v.confidence or 0:.1%}", cell),
            ]
        )
    dtable = Table(ddata, colWidths=[40 * mm, 40 * mm, 50 * mm, 20 * mm], repeatRows=1)
    dtable.setStyle(_pdf_table_style())
    story.append(dtable)

    doc.build(story)
    buf.seek(0)

    fname = f"安全{period_name}_{trend[0]['date']}_{trend[-1]['date']}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=safety_report.pdf; "
                f"filename*=UTF-8''{quote(fname)}"
            )
        },
    )
