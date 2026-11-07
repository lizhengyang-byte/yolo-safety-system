# 第 9 篇：数据驱动——看板聚合、报表导出、预警中心，以及两个大坑

> 系列博客第 9 篇。前三阶段把"脸"做漂亮了，阶段四回答更深的问题：系统积累的数据如何产生管理价值？这一篇讲看板聚合 SQL、Excel/PDF 导出，预警中心三层逻辑——以及两个真实踩过的大坑（SQLite 时间戳、reportlab 升级）。

---

## 开头：数据驱动 = 看 → 报 → 析 → 警

系统积累的违规数据，如果只是"存着"，没有任何管理价值。要让它产生价值，得回答四个层级的问题：

```
看（今天发生了什么）→ 报（这个周期如何）→ 析（哪里最严重）→ 警（正在恶化，需干预）
```

对应本项目的四个功能：
1. **看板**（`/api/logs/dashboard`）：看、析；
2. **Excel 导出**（`/export`）：报；
3. **PDF 周报/月报**（`/report`）：报、析；
4. **预警中心**（`/api/warnings/*`）：警。

## 1. 看板聚合：dashboard 的 SQLAlchemy 写法

### 接口返回什么

```python
@router.get("/dashboard")
def dashboard(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
```

返回 7 块：`total`（累计总数）、`today`（今日）、`online_cameras`（在线摄像头）、`trend`（近 N 天趋势）、`types`（类型分布）、`ranking`（摄像头排行）、`location_ranking`（点位排行）。

### 关键技术点

**① 参数校验交给 FastAPI**：`days: int = Query(7, ge=1, le=90)` —— 传 0 或 999 直接 422，业务代码不用写 if。

**② 今日统计——只比日期，不比时间**：

```python
today = db.query(func.count(Violation.id))\
    .filter(func.date(Violation.created_at) == date.today()).scalar() or 0
```

`func.date()` 转成数据库的 `DATE()` 函数，只取日期部分比较。

**③ 趋势补零（zero-fill）——最值得记住的写法**：

```python
day_rows = db.query(func.date(Violation.created_at).label("d"), func.count(Violation.id))\
    .filter(Violation.created_at >= start_dt)\
    .group_by(func.date(Violation.created_at)).all()
day_map = {str(d): c for d, c in day_rows}      # 有数据的日期才有记录

trend = []
for i in range(days - 1, -1, -1):               # 从最早一天到今天
    d = date.today() - timedelta(days=i)
    trend.append({"date": d.isoformat(), "count": day_map.get(d.isoformat(), 0)})  # 无数据补 0
```

**为什么必须补零？** 数据库只返回"有违规记录的日期"，直接画图折线会**断点**（没有 0 值）。补零后趋势图连续、"某天 0 违规"也是有效信息。这是时间序列统计的标准姿势。

**④ 点位排行（LEFT JOIN + coalesce）——跨表统计的典型写法**：

```python
loc_rows = (
    db.query(
        func.coalesce(Camera.location, "").label("loc"),
        func.count(Violation.id),
    )
    .filter(Violation.created_at >= start_dt)
    .outerjoin(Camera, Violation.camera_id == Camera.id)   # LEFT JOIN
    .group_by(func.coalesce(Camera.location, ""))
    .order_by(func.count(Violation.id).desc())
    .limit(8)
    .all()
)
location_ranking = [{"location": loc or "未填点位", "count": c} for loc, c in loc_rows]
```

三个细节：
- **`outerjoin`（LEFT JOIN）**：演示链路违规 `camera_id=0`，在 cameras 表**没有对应行**——只有 LEFT JOIN 才能把这些违规算进来（inner join 会丢数据）；
- **`coalesce`**：把 SQL NULL 变空串，Python 侧再兜底显示"未填点位"；
- **`limit(8)`**：只看 Top 8 点位。

> 🧭 这是"跨表统计 + 空值处理"的教科书写法，答辩/面试常考。

## 2. Excel 导出：筛选一致 + 内嵌图片 + 中文文件名

### 2.1 筛选复用（_build_query）

```python
def _build_query(db, violation_type=None, camera_id=None, start=None, end=None):
    q = db.query(Violation)
    if violation_type: q = q.filter(Violation.violation_type == violation_type)
    if camera_id: q = q.filter(Violation.camera_id == camera_id)
    if start: q = q.filter(Violation.created_at >= f"{start} 00:00:00")
    if end: q = q.filter(Violation.created_at <= f"{end} 23:59:59")
    return q
```

"列表与导出共用筛选"是产品需求（P1-6："导出条件与列表筛选一致"）的代码落点——导出不再是"导出全部"，而是"导出你正在看的这批"。

### 2.2 内嵌图片（openpyxl）

```python
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="安全日志")
# 再打开生成的 Excel，往里塞图片
wb = load_workbook(io.BytesIO(buffer.getvalue()))
ws = wb.active
for i, v in enumerate(rows, start=2):
    path = _resolve_image_file(v)
    if not path: continue
    xl = XLImage(path)
    xl.width, xl.height = 120, 75          # 缩略图尺寸
    ws.add_image(xl, f"{get_column_letter(img_col)}{i}")   # 锚定到"图片"列对应行
    ws.row_dimensions[i].height = 80       # 行高要加大，否则图被压扁
```

**openpyxl 的底层细节**：图片是**浮在单元格上**的（不是单元格内容），必须指定锚定单元格；行高/列宽要手动调，否则图互相遮挡。30MB 带图 Excel 实测生成成功。

### 2.3 中文文件名（跨浏览器经典坑）

```python
headers={
    "Content-Disposition": (
        f"attachment; filename=safety_logs.xlsx; "   # 兜底 ASCII 名
        f"filename*=UTF-8''{quote(fname)}"           # 真正的中文名（URL 编码）
    )
}
```

规范（RFC 5987）：`filename*` 参数用 UTF-8 编码后发送，前端 `parseFilename` 解析。**只写 `filename=安全日志.xlsx` 在旧浏览器会乱码/截断**，必须双写（ASCII 兜底 + UTF-8 扩展）。

### 2.4 CSV 兜底

```python
except Exception:
    # 无 pandas 时返回 CSV 兜底
```

用 `utf-8-sig` 编码解决 Excel 打开中文乱码。"主方案 + 兜底方案"是健壮性的体现。

## 3. PDF 安全报告（reportlab）：中文、手绘图、三个坑

### 3.1 中文方案：内置 CID 字体（最优雅的解法）

```python
_PDF_FONT = "STSong-Light"
def _ensure_pdf_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont(_PDF_FONT))   # 内置宋体，无需系统字体！
```

reportlab 内置的 `STSong-Light` 是 **CID 字体**（编码在 PDF 内部），Windows 和 Docker 都不需要装字体——**一劳永逸解决中文**。对比第 7 篇 annotate.py 的 PIL 系统字体方案（依赖 `msyh.ttc`/Noto），PDF 这里完全免依赖。

> ⚠️ 全报告所有文字（标题、表格、图表坐标轴）都要用 `fontName=_PDF_FONT`，**漏一处就出现"□□□"乱码**。

### 3.2 手绘趋势图：reportlab 4.2 重构的解法（大坑一）

**背景**：reportlab 4.2 重构了图表库，`LineChart`/`VerticalLineChart` 的经典 `data` API 失效（MRO 变为 AbstractLineChart→PlotArea→Widget，`attrmap` 里没有 `data`），只有 `HorizontalLineChart` 保留经典 API。**升级依赖导致老代码报错**——这是真实工程里最常见的坑（依赖升级 ≠ 兼容）。

**解法**：干脆不用 charts 组件，用 shapes 原语**手绘**（`_build_trend_chart`）：

```python
drawing = Drawing(470, 190)
# 网格线 + Y 刻度（4 等分）
for i in range(5):
    y = bottom + height * i / 4
    drawing.add(Line(left, y, left + width, y, strokeColor=HexColor("#ebeef5"), strokeWidth=0.5))
# 折线 + 数据点
pts = []
for i, c in enumerate(counts):
    x = left + step_x * i; y = bottom + height * c / maxc
    pts.append((x, y))
    drawing.add(Circle(x, y, 1.6, fillColor=HexColor("#f56c6c")))
drawing.add(PolyLine(pts, strokeColor=HexColor("#f56c6c"), strokeWidth=1.6))
# X 轴日期标签（间隔显示，避免 30 天标签重叠）
step = max(1, n // 8)   # 30 天只显示约 8 个日期
```

三个细节：
- **`maxc = max(counts) or 1`**：全部为 0 时避免除零（`or 1` 兜底）；
- **`n // 8` 间隔**：30 天标签不全画，防挤成一团；
- **`textAnchor = "middle"`**：日期标签居中对齐。

> 🧭 **工程教训**：第三方库升级会破坏 API。对策要么锁版本（`reportlab==4.2.5` 写在 pyproject），要么换实现（手绘）。本项目"手绘 + 锁版本"双保险。

### 3.3 PDF 结构（SimpleDocTemplate + story 流式布局）

```
story = [
    标题 + 统计区间（Paragraph）
    统计摘要表（总数/日均/今日/在线摄像头）
    违规趋势（手绘图）
    类型分布表（含占比，VIOLATION_LABELS 中文）
    点位排行表（含占比，"未填点位"兜底）
    违规明细表（前 50 条，repeatRows=1 表头跨页重复）
]
doc.build(story)
```

细节：明细表 `repeatRows=1` 让表头分页时重复出现（50 条会跨页）；空数据时显示"（窗口内暂无违规记录）"——**空状态处理是产品细节**（P2-7）。

## 4. 预警中心（warnings.py）：三层逻辑

### 4.1 触发时机（业务解耦设计）

```python
# violations.py 两条路径 + demo.py，都在 commit 之后调用：
trigger_warning_check(db, camera_id, camera_name, violation_type)
```

**为什么 commit 之后？** 注释写得清楚："统计需包含刚入库的记录"——窗口统计要数到刚插入的这条，否则每次都是"差一条才触发"。

**为什么单独一个 service？** 预警逻辑独立成 `services/warnings.py`，违规入库处只调一行函数——**业务方不感知预警细节，预警方不依赖入库流程**。

### 4.2 三层逻辑走读

```python
def trigger_warning_check(db, camera_id, camera_name, violation_type):
    # 第一层：冷却检查——10 分钟内同 camera+type 已触发过则直接返回
    if _recent_event_exists(db, camera_id, violation_type):
        return
    # 第二层：规则匹配——enabled 且（camera_id/type 为空=全部，否则必须相等）
    rules = db.query(WarningRule).filter(WarningRule.enabled.is_(True)).all()
    for rule in rules:
        if not _rule_matches(rule, camera_id, violation_type):
            continue
        # 第三层：窗口统计——最近 window_minutes 分钟该摄像头该类型违规数
        count = _window_count(db, camera_id, violation_type, rule.window_minutes)
        if count >= rule.threshold:
            db.add(WarningEvent(rule_id=rule.id, ..., count=count))
            db.commit()
            return          # 命中一条规则即可
```

```python
def _rule_matches(rule, camera_id, violation_type):
    if not rule.enabled: return False
    if rule.camera_id is not None and rule.camera_id != camera_id: return False   # None=全部
    if rule.violation_type is not None and rule.violation_type != violation_type: return False
    return True
```

```python
def _recent_event_exists(db, camera_id, violation_type):
    since = datetime.now() - timedelta(minutes=EVENT_COOLDOWN_MINUTES)   # 10 分钟
    return count(WarningEvent, camera_id==.., violation_type==.., triggered_at >= since) > 0

def _window_count(db, camera_id, violation_type, window_minutes):
    since = datetime.now() - timedelta(minutes=window_minutes)
    return count(Violation, camera_id==.., type==.., created_at >= since)
```

**设计点评**：

1. **"空值=通配"让规则模型优雅**（对应 models.py 的 `nullable=True` 设计，第 6 篇）；
2. **冷却防刷屏**：持续违规时 10 分钟只生成一条事件，但事件里记录"窗口内累计次数"（count）——**信息不丢，噪声可控**；
3. **`return` 提前结束**：命中第一条匹配规则即可，避免一个违规插入多个事件。

> ⚠️ **注意**：`_window_count` 依赖 `created_at`（本地时间写入）。这正是时间戳陷阱（下节）的直接后果——时间存 UTC 的话，这里统计永远算不清。

## 5. 大坑二：SQLite 时间戳 UTC 陷阱（本项目最痛的坑）

### 5.1 现象

阶段四实现预警后实测发现：**窗口统计永远为 0，预警永远不触发**。查库发现：

```
数据库里记录：2026-11-06 06:05:34
系统当前时间：2026-11-06 14:06:00   ← 差了 8 小时！
```

### 5.2 根因

SQLAlchemy 的 `server_default=_func.now()` 在 SQLite 上生成 `CURRENT_TIMESTAMP`，而 **SQLite 的 CURRENT_TIMESTAMP 返回 UTC 时间**。业务层用 `datetime.now()`（本地时间，UTC+8）比较 → 窗口内的违规**永远"不够"**：

```
实际 14:00 发生的违规，库里记 06:00
窗口起点 since = 现在(14:00) - 60min = 13:00
06:00 >= 13:00 → False → 统计不到 → 预警永不触发 ✗
```

### 5.3 修复

```python
# models.py：时间戳统一用 Python 本地时间写入
_ts = datetime.now
created_at = Column(DateTime, default=_ts, index=True)
```

- **新数据**：`default=datetime.now`（Python 侧，本地时间）——与业务比较口径一致；
- **存量数据**：一次性迁移 `UPDATE violations SET created_at = datetime(created_at, '+8 hours')`（以及 cameras 表）；
- **MySQL 无此问题**：MySQL 的 `NOW()` 本来就是服务器本地时间。

> ⚠️ CLAUDE.md 警告：**不要改回 `server_default=_func.now()`**——这是踩坑后立的规矩。

### 5.4 教训（值得背下来）

1. **时间戳必须明确"存储口径"**：UTC 还是本地？写入时是谁的时间？
2. **跨数据库移植时，时间函数语义不同**（SQLite CURRENT_TIMESTAMP=UTC vs MySQL NOW()=本地）；
3. **统一原则**：要么全部 UTC 存储 + 展示层转本地，要么全部本地存储（本项目方案）；**最忌讳混用**；
4. **写测试验证时间边界**：预警/今日统计这类"依赖时间比较"的功能，实测一次才知道。

## 总结

- **看板**：参数校验交给 FastAPI、趋势 zero-fill、LEFT JOIN + coalesce 跨表统计、"未填点位"兜底；
- **Excel**：筛选复用（_build_query）、openpyxl 内嵌图片（锚定单元格 + 调行高）、filename* 中文名、CSV 兜底；
- **PDF**：STSong-Light CID 中文免依赖、reportlab 4.2 图表重构 → shapes 手绘、repeatRows 表头跨页、空状态文案；
- **预警**：commit 后触发、冷却防刷屏、空值=通配、窗口统计；
- **两个大坑**：SQLite 时间戳（UTC 差 8 小时）→ 统一本地时间；reportlab 升级 → 手绘兜底 + 锁版本。

**下一篇：[第 10 篇：一个人 + AI，几天搭完一套系统——用 Claude Code 快速开发全流程](10-AI辅助开发-用Claude Code快速搭建全流程.md)**
