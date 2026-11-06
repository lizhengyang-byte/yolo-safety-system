"""安全日志：统计 + 数据看板聚合 + Excel 导出（含违规图片）"""
import io
import os
from datetime import date, timedelta
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Camera, Violation

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
def dashboard(db: Session = Depends(get_db)):
    """数据看板聚合接口：总数 / 今日 / 在线摄像头 / 近7天趋势 / 类型分布 / 摄像头排行"""
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

    # 近 7 天趋势（含 0 天）
    day_rows = (
        db.query(func.date(Violation.created_at).label("d"), func.count(Violation.id))
        .group_by(func.date(Violation.created_at))
        .all()
    )
    day_map = {str(d): c for d, c in day_rows}
    trend = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        trend.append({"date": d.isoformat(), "count": day_map.get(d.isoformat(), 0)})

    # 类型分布
    type_rows = (
        db.query(Violation.violation_type, func.count(Violation.id))
        .group_by(Violation.violation_type)
        .all()
    )
    types = [{"type": t, "count": c} for t, c in type_rows]

    # 摄像头违规排行
    cam_rows = (
        db.query(Violation.camera_name, func.count(Violation.id))
        .group_by(Violation.camera_name)
        .order_by(func.count(Violation.id).desc())
        .limit(10)
        .all()
    )
    ranking = [{"name": n or "未知", "count": c} for n, c in cam_rows]

    return {
        "total": total,
        "today": today,
        "online_cameras": online,
        "trend": trend,
        "types": types,
        "ranking": ranking,
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
