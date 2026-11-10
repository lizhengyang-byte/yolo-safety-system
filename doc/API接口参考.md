# API 接口参考：工地 AI 安全监测系统后端

> 本参考基于 `backend/app/routers/` 实际代码整理，覆盖全部 25+ 个接口，含 curl 示例、请求/响应格式与常见错误。
> 调试最快的方式：启动后端后直接打开 **`http://localhost:8000/docs`**（FastAPI 自动生成的可交互 Swagger）。

- **Base URL（本地开发）：** `http://localhost:8000`（Docker 部署时前端经 nginx 反代 `/api`）
- **API 前缀：** 所有业务接口均为 `/api/*`
- **图片访问：** 抓拍图片挂载在 `/images/*`（静态目录）
- **接口文档：** `/docs`（Swagger UI）、`/redoc`
- **更新时间：** 2026-11-06

## 目录

- [认证与鉴权](#认证与鉴权)
- [错误处理](#错误处理)
- [端点一览](#端点一览)
- [认证接口](#认证接口)
- [摄像头接口](#摄像头接口)
- [违规记录接口](#违规记录接口)
- [日志与报表接口](#日志与报表接口)
- [演示接口](#演示接口)
- [预警中心接口](#预警中心接口)
- [实时推送（SSE）](#实时推送sse)
- [危险区域接口（多边形 ROI）](#危险区域接口多边形-roi)
- [系统配置（邮件与报告）](#系统配置邮件与报告)
- [最佳实践](#最佳实践)

---

## 认证与鉴权

本系统使用 **JWT**（HS256）认证。

**获取 token：**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**响应：**

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer" }
```

**使用 token：** 前端 `utils/request.ts` 拦截器会自动附加请求头：

```
Authorization: Bearer <access_token>
```

> ⚠️ **当前鉴权状态（诚实说明）：** 后端目前仅在登录接口签发 JWT；业务接口暂未强制校验（`security.py` 已提供 `get_current_user` 依赖，接入时在各路由加 `Depends(get_current_user)` 即可）。前端对 401 已做跳转登录处理，为的是给前端路由守卫用。**生产环境请务必给业务接口加鉴权。**

---

## 错误处理

统一由 FastAPI 处理，错误响应格式：

```json
{ "detail": "错误描述" }
```

| 状态码 | 含义 | 常见场景 |
|---|---|---|
| 200 / 201 | 成功 | 201 用于创建类接口（POST） |
| 400 | 参数错误 | `demo/detect` 图片解码失败 |
| 401 | 未认证 | 登录失败（用户名或密码错误） |
| 404 | 资源不存在 | 摄像头/规则 ID 不存在 |
| 422 | 参数校验失败 | Query/Form/JSON 字段非法（如 `days=999` 超出 `le=90`） |
| 500 | 服务器内部错误 | 依赖缺失 / 未捕获异常 |
| 503 | 服务不可用 | 演示模型 `ppe.pt` 未找到 |

---

## 端点一览

| 分组 | 方法与路径 | 说明 |
|---|---|---|
| 认证 | `POST /api/auth/login` | 登录获取 JWT |
| 健康 | `GET /api/health` | 健康检查 |
| 摄像头 | `GET /api/cameras` | 摄像头列表 |
| 摄像头 | `POST /api/cameras` | 新增摄像头 |
| 摄像头 | `POST /api/cameras/test` | RTSP 连通性测试（8s 兜底） |
| 摄像头 | `GET /api/cameras/{id}` | 单台详情 |
| 摄像头 | `PUT /api/cameras/{id}` | 更新（部分字段） |
| 摄像头 | `DELETE /api/cameras/{id}` | 删除 |
| 摄像头 | `POST /api/cameras/{id}/status` | 推理服务心跳更新在线状态 |
| 违规 | `POST /api/violations` | 上报违规（仅元数据） |
| 违规 | `POST /api/violations/with-image` | 上报违规（multipart 带图） |
| 违规 | `GET /api/violations` | 违规分页列表（多条件筛选） |
| 日志 | `GET /api/logs/stats` | 违规类型统计 |
| 日志 | `GET /api/logs/dashboard` | 数据看板聚合（基础字段 + 大屏增强：环比/小时分布/最新抓拍/摄像头状态/预警摘要） |
| 日志 | `GET /api/logs/export` | 导出 Excel（内嵌图片）/ CSV 兜底 |
| 日志 | `GET /api/logs/report` | 下载 PDF 周报/月报 |
| 日志 | `POST /api/logs/report/email` | 生成报告 PDF 并邮件发送（`period=week\|month`） |
| 演示 | `GET /api/demo/status` | 演示环境自检 |
| 演示 | `POST /api/demo/detect` | 帧检测 + 违规抓拍入库 |
| 预警 | `GET /api/warnings/rules` | 预警规则列表 |
| 预警 | `POST /api/warnings/rules` | 新增规则 |
| 预警 | `PUT /api/warnings/rules/{id}` | 更新规则 |
| 预警 | `DELETE /api/warnings/rules/{id}` | 删除规则 |
| 预警 | `GET /api/warnings/events` | 预警事件分页（可筛未读） |
| 预警 | `GET /api/warnings/unread-count` | 未读事件数（SSE 实时刷新，60s 轮询兜底） |
| 预警 | `POST /api/warnings/events/read` | 按 ID 列表标已读 |
| 预警 | `POST /api/warnings/events/read-all` | 全部标已读 |
| 预警 | `POST /api/warnings/email/test` | 预警邮件自检（未配置返回提示） |
| 实时 | `GET /api/realtime/stream` | SSE 实时推送（`violation` / `warning` / `camera_status`） |
| 危险区域 | `GET /api/zones` | 危险区域列表（可按 `camera_id` 过滤） |
| 危险区域 | `POST /api/zones` | 新增危险区域（归一化多边形） |
| 危险区域 | `PUT /api/zones/{id}` | 更新危险区域 |
| 危险区域 | `DELETE /api/zones/{id}` | 删除危险区域 |
| 配置 | `GET/PUT /api/settings/mail` | 邮件 SMTP 配置读写（密码脱敏） |
| 配置 | `POST /api/settings/mail/test` | 发送测试邮件 |
| 配置 | `GET/PUT /api/settings/report` | 报告推送配置（预警邮件/日报/周报/收件人） |
| 配置 | `POST /api/settings/report/send` | 立即发送报告（`period=daily\|week\|month`） |

---

## 认证接口

### 登录

**Endpoint:** `POST /api/auth/login`

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | string | 是 | 管理员用户名（默认 `admin`） |
| `password` | string | 是 | 密码（默认 `admin123`） |

**示例：**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**响应 200：**

```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

**错误：** `401` 用户名或密码错误。

---

## 摄像头接口

### 列出摄像头

**Endpoint:** `GET /api/cameras`

返回全部摄像头（按 id 升序）。

**响应 200：**

```json
[
  {
    "id": 1,
    "name": "1号塔吊",
    "location": "A区",
    "rtsp_url": "rtsp://user:pass@192.168.1.10:554/stream",
    "enabled": true,
    "status": "online",
    "created_at": "2026-11-01T10:00:00"
  }
]
```

> `status` 由推理服务心跳（`POST /api/cameras/{id}/status`）维护：`online` / `offline`。

### 新增摄像头

**Endpoint:** `POST /api/cameras`

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 名称（≤64 字符） |
| `location` | string | 否 | 点位/安装位置（默认空串） |
| `rtsp_url` | string | 是 | RTSP 地址 |
| `enabled` | bool | 否 | 是否启用（默认 `true`） |

**响应 201：** 创建的 Camera 对象（同上结构）。

### 测试 RTSP 连通性

**Endpoint:** `POST /api/cameras/test`

**请求体（JSON）：** `{ "rtsp_url": "rtsp://..." }`

**说明：** 独立线程探测，**8 秒兜底超时**（不阻塞事件循环）。地址不可达 / 读不到画面时返回可读中文。

**响应 200：**

```json
{ "ok": true, "message": "连接成功，可正常拉流" }
```

**失败示例：** `{ "ok": false, "message": "连接超时（8 秒）：请确认地址格式 rtsp://账号:密码@IP:554/stream，且本机可访问该网络" }`

### 获取单个摄像头

**Endpoint:** `GET /api/cameras/{id}`

**错误：** `404` 摄像头不存在。

### 更新摄像头

**Endpoint:** `PUT /api/cameras/{id}`

**请求体：** 部分字段即可（`name` / `location` / `rtsp_url` / `enabled` 任一），`exclude_unset` 只更新传入字段。

### 删除摄像头

**Endpoint:** `DELETE /api/cameras/{id}`

**响应 200：** `{ "message": "删除成功" }`

### 更新在线状态（推理服务心跳）

**Endpoint:** `POST /api/cameras/{id}/status?status=online`

**Query：** `status`（string，必填，如 `online` / `offline`）

**调用方：** `inference/stream_worker.py` 定期心跳，后端据此更新摄像头上线/离线状态。

---

## 违规记录接口

### 上报违规（仅元数据）

**Endpoint:** `POST /api/violations`

**用途：** 推理服务检测到违规后调用（图片已另存时的轻量上报）。

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `camera_id` | int | 是 | 摄像头 ID（演示链路为 0） |
| `camera_name` | string | 否 | 摄像头名（默认空串） |
| `violation_type` | string | 是 | 违规 key：`no_helmet` / `no_vest` / `no_mask` |
| `confidence` | float | 否 | 置信度（默认 0.0） |

**响应 201：** `ViolationOut` 对象。

> ⚠️ 本接口 `image_url` 为空（无图片）。**实际生产路径建议用 `with-image`**。

### 上报违规（multipart 带图）★ 核心接口

**Endpoint:** `POST /api/violations/with-image`

**用途：** 推理服务直接 POST 图片 + 违规信息，后端保存图片并入库。**正式链路的上报入口。**

**请求（multipart/form-data）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 原始帧 JPEG（存为 `image_url`） |
| `anno` | file | 否 | 标注证据图（存为 `anno_url`，推理服务已画框） |
| `detections` | string | 否 | 帧内检测明细 JSON（违规详情页表格展示） |
| `camera_id` | int | 是 | 摄像头 ID |
| `camera_name` | string | 否 | 摄像头名 |
| `violation_type` | string | 是 | 违规 key |
| `confidence` | float | 否 | 置信度 |

**curl 示例：**

```bash
curl -X POST http://localhost:8000/api/violations/with-image \
  -F "file=@v_1_20261106140530.jpg" \
  -F "anno=@v_1_20261106140530_anno.jpg" \
  -F 'detections=[{"cls_name":"NO-Hardhat","conf":0.87,"box":[120,45,310,280]}]' \
  -F "camera_id=1" -F "camera_name=1号塔吊" \
  -F "violation_type=no_helmet" -F "confidence=0.87"
```

**响应 201：**

```json
{
  "id": 1024,
  "camera_id": 1,
  "camera_name": "1号塔吊",
  "violation_type": "no_helmet",
  "confidence": 0.87,
  "image_url": "/images/v_1_20261106140530.jpg",
  "anno_url": "/images/v_1_20261106140530_anno.jpg",
  "detections": [{ "cls_name": "NO-Hardhat", "conf": 0.87, "box": [120, 45, 310, 280] }],
  "created_at": "2026-11-06T14:05:30"
}
```

**实现细节：**
- 文件名含毫秒级时间戳（`v_{camera_id}_{%Y%m%d%H%M%S%f}` 去后 3 位），避免同秒多帧互相覆盖；
- `detections` JSON 非法会被忽略（不影响上报）；
- **commit 后自动触发预警规则检查**（`trigger_warning_check`）。

### 违规分页列表

**Endpoint:** `GET /api/violations`

**Query 参数：**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `page` | int | 1 | 页码（≥1） |
| `page_size` | int | 20 | 每页条数（1~100） |
| `violation_type` | string | - | 按违规类型筛选 |
| `camera_id` | int | - | 按摄像头筛选 |
| `start` | string | - | 开始日期 `YYYY-MM-DD`（当日 00:00:00 起） |
| `end` | string | - | 结束日期 `YYYY-MM-DD`（当日 23:59:59 止） |

**响应 200：**

```json
{
  "total": 42,
  "items": [ { "id": 1024, "camera_id": 1, "camera_name": "1号塔吊", "violation_type": "no_helmet", "confidence": 0.87, "image_url": "/images/v_1_...jpg", "anno_url": "/images/v_1_..._anno.jpg", "detections": [...], "created_at": "2026-11-06T14:05:30" } ]
}
```

---

## 日志与报表接口

### 违规类型统计

**Endpoint:** `GET /api/logs/stats`

**响应 200：**

```json
{
  "total": 120,
  "detail": [ { "type": "no_helmet", "count": 80 }, { "type": "no_mask", "count": 40 } ]
}
```

### 数据看板聚合

**Endpoint:** `GET /api/logs/dashboard?days=7`

**Query 参数：** `days`（int，默认 7，范围 1~90；传 0 或 999 直接 422）。

**响应 200（7 块数据）：**

```json
{
  "total": 120,
  "today": 5,
  "online_cameras": 3,
  "trend": [ { "date": "2026-10-31", "count": 0 }, { "date": "2026-11-01", "count": 2 } ],
  "types": [ { "type": "no_helmet", "count": 80 }, { "type": "no_mask", "count": 40 } ],
  "ranking": [ { "name": "1号塔吊", "count": 60 } ],
  "location_ranking": [ { "location": "A区", "count": 60 } ]
}
```

**实现要点：**
- `trend` 按天 **zero-fill 补零**（无记录日期 count=0），折线连续；
- `location_ranking` 用 `violations LEFT JOIN cameras` + `coalesce`，演示违规（`camera_id=0`）也能统计；空点位显示"未填点位"；
- `days` 切换窗口（7/30/90），前端看板工具栏对应下拉。

### 导出 Excel 安全日志

**Endpoint:** `GET /api/logs/export`

**Query 参数：** 与列表筛选一致——`violation_type` / `camera_id` / `start` / `end`（**导出的是"你正在看的那批"，不是全量**）。上限 `EXPORT_ROW_LIMIT=5000` 行。

**响应 200：** Excel 文件（`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`），内嵌违规图片缩略图（120×75），中文文件名：

```
Content-Disposition: attachment; filename=safety_logs.xlsx; filename*=UTF-8''%E5%AE%89%E5%85%A8%E6%97%A5%E5%BF%97_....xlsx
```

**兜底：** 无 pandas/openpyxl 时回退 CSV（`utf-8-sig` 编码，Excel 打开无乱码）。

**curl 示例：**

```bash
curl -X GET "http://localhost:8000/api/logs/export?violation_type=no_helmet&start=2026-11-01&end=2026-11-06" -o 安全日志.xlsx
```

### 导出 PDF 安全报告

**Endpoint:** `GET /api/logs/report?period=week`

**Query 参数：** `period`（`week` 周报近 7 天 / `month` 月报近 30 天；非法值 422）。

**响应 200：** PDF 文件。内容：统计摘要（总数/日均/今日/在线摄像头）→ 手绘违规趋势图 → 类型分布表 → 点位排行表 → 前 50 条违规明细。

**实现要点：** 中文字体用 reportlab 内置 `STSong-Light` CID（无需系统字体）；趋势图用 shapes 原语手绘（reportlab 4.2 后 LineChart `data` API 失效）。

---

## 演示接口

### 演示环境自检

**Endpoint:** `GET /api/demo/status`

**用途：** 演示页"环境自检"按钮——一次性确认摄像头权限/后端连通/模型就绪。

**响应 200：**

```json
{
  "model_loaded": false,
  "model_path": "weights/ppe/ppe.pt",
  "device": "cpu",
  "conf_threshold": 0.5
}
```

### 帧检测（演示核心接口）

**Endpoint:** `POST /api/demo/detect`

**用途：** 接收前端摄像头帧（JPEG），返回检测框 + 违规类型；违规时自动抓拍入库。**监控页 AI 叠加也复用本接口**（`no_save=true`）。

**请求（multipart/form-data）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 单帧 JPEG |
| `no_save` | bool | 否 | `true` 时只检测不入库（监控叠加用） |
| `conf` | float | 否 | 本次置信度阈值覆盖（演示页"灵敏度"滑块），`null` 用默认 0.5 |

**curl 示例：**

```bash
curl -X POST http://localhost:8000/api/demo/detect \
  -F "file=@frame.jpg" \
  -F "conf=0.5"
```

**响应 200（无违规 / no_save）：**

```json
{
  "detections": [
    { "cls_id": 2, "cls_name": "NO-Hardhat", "conf": 0.87, "box": [120.0, 45.0, 310.0, 280.0] }
  ],
  "violations": ["no_helmet"],
  "snapshot_url": null
}
```

**响应 200（违规且未 no_save）：** `snapshot_url` 为标注证据图地址；违规自动抓拍（原始帧 + 标注证据图）并以 `camera_id=0`、`camera_name="临时演示"` 入库。

**实现要点：**
- 模型懒加载单例 + 双重检查锁（首次加载 10~30s，后端启动已预热）；
- 推理放 `run_in_threadpool`，不阻塞事件循环；
- `conf` 调高 = 更严格（只认高置信度），调低 = 更敏感。

**错误：** `400` 图片解码失败；`503` 未找到演示模型 `ppe.pt`。

---

## 预警中心接口

### 规则 CRUD

**GET /api/warnings/rules** — 全部规则（按 id 降序）。

**POST /api/warnings/rules** — 新增规则。

**请求体（JSON）：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 规则名（≤64 字符） |
| `camera_id` | int | 否 | 摄像头 ID，**null=全部** |
| `violation_type` | string | 否 | 违规类型，**null=全部** |
| `threshold` | int | 否 | 次数阈值（1~10000，默认 3） |
| `window_minutes` | int | 否 | 时间窗口分钟（1~1440，默认 60） |
| `enabled` | bool | 否 | 是否启用（默认 true） |

**PUT /api/warnings/rules/{id}** — 部分更新（`exclude_unset`）。`404` 规则不存在。

**DELETE /api/warnings/rules/{id}** — 删除。`404` 规则不存在。

### 预警事件

**GET /api/warnings/events?page=1&page_size=20&unread_only=false**

分页查询；`unread_only=true` 只返回未读。按 `triggered_at` 降序。

**响应：**

```json
{
  "total": 3,
  "items": [
    {
      "id": 1,
      "rule_id": 2,
      "camera_id": 1,
      "camera_name": "1号塔吊",
      "violation_type": "no_helmet",
      "count": 5,
      "triggered_at": "2026-11-06T13:00:00",
      "is_read": false
    }
  ]
}
```

### 未读数（顶栏铃铛）

**Endpoint:** `GET /api/warnings/unread-count`

**响应：** `{ "count": 3 }`

前端主布局优先通过 SSE（`/api/realtime/stream`）实时刷新，60s 轮询仅作兜底。

### 标记已读

**`POST /api/warnings/events/read?ids=1&ids=2`** — 按 ID 列表标已读。

**响应：** `{ "message": "已标记 2 条为已读" }`

**`POST /api/warnings/events/read-all`** — 全部标已读。

**响应：** `{ "message": "已全部标记为已读（3 条）" }`

### 触发逻辑（了解即可）

预警**不是手动触发**的接口，而是违规入库（`with-image` / `demo/detect` 两条路径）commit 后自动调用 `services/warnings.py::trigger_warning_check`：

```
① 10 分钟冷却（同 camera+type 冷却期内不再生成）
② 规则匹配（enabled=true，camera_id/type 空=通配）
③ 窗口统计（最近 window_minutes 分钟该摄像头该类型违规数 ≥ threshold → 生成事件）
④ 事件生成后：SSE 推送 warning 事件；若「预警邮件」开启且 SMTP 已配置，后台线程发送邮件（正文 + 该摄像头/类型最近一条抓拍图附件）
```

---

## 实时推送（SSE）

**Endpoint:** `GET /api/realtime/stream?token=<JWT>`

EventSource 无法设置 Authorization 头，故 token 走 query。响应为 `text/event-stream`，每 15s 发一次注释心跳（`: ping`）。

| event | data 字段 |
|---|---|
| `violation` | `id / camera_id / camera_name / location / violation_type / confidence / image_url / anno_url / created_at` |
| `warning` | `id / camera_id / camera_name / location / violation_type / type_label / count / triggered_at / is_read / confidence` |
| `camera_status` | `id / name / location / status` |

前端 `composables/useRealtime.ts` 全局共享一条连接，断线自动重连；看板/顶栏/大屏均改为事件驱动（60s 轮询兜底）。

---

## 危险区域接口（多边形 ROI）

危险区域（`danger_zones` 表）绑定到具体摄像头，用于"人员闯入危险区"判定（违规类型 `zone_intrusion`）。多边形坐标为**归一化值**（0~1，相对画面宽高），推理服务按 `camera_id` 拉取后实时判定。

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/zones?camera_id=` | 列出危险区域（可按摄像头过滤；camera_id 省略返回全部） |
| `POST` | `/api/zones` | 新增区域（多边形至少 3 点、坐标 0~1，非法返回 400） |
| `PUT` | `/api/zones/{id}` | 更新区域（名称/类别/多边形/阈值/启用状态，均可选） |
| `DELETE` | `/api/zones/{id}` | 删除区域 |

**字段说明：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `camera_id` | int | 绑定摄像头 ID |
| `zone_name` | str | 区域名称（如"深基坑西侧"） |
| `zone_type` | str | `danger`（配电房/危险区）/ `pit`（基坑）/ `lifting`（吊装区）/ `other` |
| `polygon` | `[[x,y],...]` | 归一化多边形顶点（0~1） |
| `min_confidence` | float | 人员检测置信度阈值，默认 0.4 |
| `min_dwell_seconds` | float | 停留时长阈值（秒），默认 2.0；路过不触发 |
| `enabled` | bool | 是否启用 |

**新增示例：**

```bash
curl -X POST http://localhost:8000/api/zones \
  -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" \
  -d '{
    "camera_id": 1, "zone_name": "深基坑西侧", "zone_type": "pit",
    "polygon": [[0.2,0.3],[0.6,0.3],[0.6,0.8],[0.2,0.8]],
    "min_confidence": 0.45, "min_dwell_seconds": 3.0, "enabled": true
  }'
```

**响应（201）：** 返回含 `id`、`polygon`（解析后的数组）、`created_at` 的完整区域对象。

> 判定在推理服务侧完成：`zone.py` 取 Person 框底边中点归一化，射线法判内点 + 置信度过滤 + 停留时长累积，命中则上报 `violation_type=zone_intrusion` 并抓拍（证据图叠加紫红多边形）。

---

## 系统配置（邮件与报告）

配置持久化在 `system_settings` 表（网页值优先于 `.env` 默认值），保存即生效。

### 邮件 SMTP

- `GET /api/settings/mail` → 返回配置（`password` 脱敏为 `******`，另含 `has_password`）。
- `PUT /api/settings/mail` → 字段：`enabled / host / port / user / password / ssl / starttls / from / to`（`password` 留空或为掩码表示不修改）。
- `POST /api/settings/mail/test` → `{ "ok": true, "message": "..." }`。

### 报告推送

- `GET /api/settings/report` → `warning_email_enabled / daily_enabled / daily_time / weekly_enabled / weekly_day / weekly_time / report_to / last_daily_sent / last_weekly_sent / effective_to`。
- `PUT /api/settings/report` → 同上可写字段。
- `POST /api/settings/report/send?period=daily|week|month` → 立即生成并发送。

### 报告邮件（看板导出）

`POST /api/logs/report/email?period=week|month` → 生成 PDF 并作为附件发送；未配置 SMTP/收件人返回 400。

> 每日/每周报告由后端 `services/report_scheduler.py` 后台线程每 30 秒检查配置时间自动发送（当天已发不重复）。

---

## 最佳实践

### 1. 上传图片用 multipart

带图上报必须用 `POST /api/violations/with-image`（form-data），业务字段（camera_id 等）放 Form 字段；`/api/violations` 仅用于无图场景。

### 2. 分页与筛选

列表接口统一 `page` + `page_size`（≤100）；导出接口的筛选条件与列表**一致**（`_build_query` 复用）。

### 3. 中文文件名

导出接口用 RFC 5987 双写：`filename=...; filename*=UTF-8''<url编码>`。前端用 `utils/download.ts` 的 `parseFilename` 解析。

### 4. 时间口径

所有时间字段为**本地时间**（Python `datetime.now` 写入）。比对日期用 `YYYY-MM-DD`（`start` 当日 00:00:00 起、`end` 当日 23:59:59 止）。

### 5. 调试建议

- 优先用 `/docs` 的 Swagger 交互测试（可直接传文件、看 schema）；
- 推理服务 → 后端的数据流可用 `with-image` 的 curl 示例手工模拟（配合「手工上报」实验）。

---

## Support

- 完整教程与底层原理：`doc/` 系列博客（[doc/README.md](./README.md)）
- 架构与设计决策：[doc/ARCHITECTURE.md](./ARCHITECTURE.md)
- 源码：`backend/app/routers/`（每个文件头都有接口职责注释）
- 数据库结构：`backend/app/models.py`、`backend/init.sql`
