"""安全日志：统计 + Excel 导出"""
import io
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Violation

router = APIRouter()


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


@router.get("/export")
def export_excel(
    violation_type: str = Query(None),
    start: str = Query(None),
    end: str = Query(None),
    db: Session = Depends(get_db),
):
    """导出安全日志为 Excel"""
    q = db.query(Violation)
    if violation_type:
        q = q.filter(Violation.violation_type == violation_type)
    if start:
        q = q.filter(Violation.created_at >= f"{start} 00:00:00")
    if end:
        q = q.filter(Violation.created_at <= f"{end} 23:59:59")
    rows = q.order_by(Violation.created_at.desc()).all()

    try:
        import pandas as pd

        data = [
            {
                "ID": v.id,
                "摄像头": v.camera_name,
                "违规类型": v.violation_type,
                "置信度": round(v.confidence or 0, 3),
                "抓拍时间": v.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if v.created_at
                else "",
                "图片地址": v.image_url,
            }
            for v in rows
        ]
        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="安全日志")
        buffer.seek(0)
        filename = "safety_logs.xlsx"
        return StreamingResponse(
            buffer,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
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
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=safety_logs.csv"},
        )
