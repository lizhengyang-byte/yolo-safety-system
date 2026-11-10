# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

工地 AI 安全监测系统（YOLO 版）：对接 RTSP 监控摄像头，用 YOLOv8 实时识别未戴安全帽 / 未穿马甲 / 未戴口罩等违规，自动抓拍留痕入库，并提供 Vue3 后台管理。仓库同时保留原始视频检测脚本。

核心约定：**当前仓库已适配根目录 `ppe.pt` 模型（10 类，直接输出违规类 `NO-*`）**，违规判定为 `direct` 模式。所有代码注释、README、配置均按此约定编写，改动时保持一致性。

## 常用命令

### 本地开发（不用 Docker，默认 SQLite，零 MySQL 依赖）

```bash
# 后端（SQLite，自动建表，端口 8000）
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 推理服务（RTSP 拉流 + 检测 + 上报）
# 注意：推理服务必须从仓库根目录启动（inference 是包名，非顶层目录）
cd ..
CONFIG_PATH=inference/config.local.yaml uv run python -m inference.main

# 前端（端口 3000，已代理 /api 与 /images 到 localhost:8000）
cd frontend
npm install
npm run dev
```

一键启动：根目录 `start-local.bat`（启动后端 + 前端，推理服务默认注释掉，需先录入摄像头再取消注释）。

### Docker 部署

```bash
docker compose up -d --build
# 前端 http://localhost | 后端接口 http://localhost:8000/docs
# 默认账号 admin / admin123
```

Docker 环境由 `docker-compose.yml` 通过环境变量覆盖：`DATABASE_URL` 指向 MySQL、`UPLOAD_DIR=/data/images`。

### 原始脚本（根目录，视频文件 PPE 检测，共用 ppe.pt）

```bash
uv sync                                    # 根目录 pyproject.toml
uv run python Safety-Detection.py                                   # 实时窗口播放
uv run python Safety-Detection-export-gpu.py --input videos/x.mp4 --output videos/x_out.mp4 --half
```

本项目**没有配置测试与 lint**（无 pytest、无 ESLint 脚本）。

## 架构总览

仓库是 **yolo-safety-system**（backend / frontend / inference / deploy）与原始 Safety-Detection 脚本的合并。完整数据流：

```
RTSP 摄像头 → MediaMTX 转发(8554/8080) → 推理服务(OpenCV 拉流)
  → YOLOv8 检测 → 违规判定(direct/IoU) → 自动抓拍
  → POST /api/violations/with-image → FastAPI 入库(SQLite/MySQL)
  → Vue3 后台展示 / 导出
```

### 三条业务链路

1. **正式链路**：`inference/main.py` 从后端拉取启用摄像头列表，每摄像头一个 `StreamWorker` 线程（`stream_worker.py`）。循环拉流 → 每 N 帧检测 → `judge_violations` 判定 → 命中时去重（`dedup_seconds`）保存图片并 multipart 上报后端。无启用摄像头时服务直接退出。**每个摄像头的 worker 同时并行运行 PPE 模型与火源/烟雾模型**（见下「火源火灾检测」）。
2. **临时演示链路**：前端 `views/demo/index.vue` 用 `getUserMedia` 取帧，每 500ms POST `/api/demo/detect`（`routers/demo.py`），后端直接加载模型推理（懒加载单例 + 启动预热线程），违规时以 `camera_id=0`、`camera_name="临时演示"` 入库。流程与正式链路判定逻辑一致（同样 PPE + 火源双模型并行）。
3. **原始脚本**：根目录三个 `Safety-Detection*.py`，独立于系统，仅做本地视频标注导出。

### 关键：检测/判定/标注代码刻意双份、必须同步

以下文件在 `inference/` 与 `backend/app/detection/` 之间**逐行一致**（后端演示模式复用同一套逻辑，因后端独立加载模型而复制），修改任意一处必须同步另一处：

- `detector.py`（YOLO 封装，`predict` 支持 conf 阈值覆盖）
- `judge.py`（违规判定）
- `annotate.py`（抓拍标注证据图绘制：检测框 + 中文违规横幅）

### 新接口一览（产品功能优化后）

| 接口 | 说明 |
|---|---|
| `GET /api/logs/dashboard` | 数据看板聚合：总数/今日/在线摄像头/趋势/类型分布/摄像头排行/**点位排行**；`days` 参数切换窗口（7/30/90，趋势按天 zero-filled） |
| `GET /api/logs/export` | 导出增强：支持 camera_id 筛选，Excel 内嵌违规图片缩略图，中文文件名 |
| `GET /api/logs/report` | PDF 安全报告导出（`period=week\|month` 周报/月报）：统计摘要 + 手绘趋势折线图 + 类型分布 + 点位排行 + 前 50 条明细；reportlab 内置 `STSong-Light` CID 中文字体（Windows/Docker 无需系统字体，勿用 4.2 重构后的 LineChart data API，见 `_build_trend_chart` 手绘实现） |
| `GET /api/demo/status` | 演示环境自检：模型是否已加载/路径/设备/默认阈值 |
| `POST /api/demo/detect` | 支持 `conf`（置信度覆盖，灵敏度滑块）与 `no_save=true`（仅检测不入库，监控页 AI 叠加复用） |
| `POST /api/violations/with-image` | 支持 `anno`（标注证据图）与 `detections`（帧内检测明细 JSON）字段；入库后自动触发预警规则检查 |
| `POST /api/cameras/test` | RTSP 连通性测试（8 秒兜底，不可阻塞事件循环） |
| `GET/POST /api/warnings/rules`、`PUT/DELETE /api/warnings/rules/{id}` | 预警规则 CRUD（camera_id 空=全部、violation_type 空=全部、threshold、window_minutes、enabled） |
| `GET /api/warnings/events` | 预警事件分页（`unread_only` 筛选） |
| `GET /api/warnings/unread-count` | 未读预警数（SSE 实时刷新，60s 轮询兜底） |
| `POST /api/warnings/events/read?ids=..`、`POST /api/warnings/events/read-all` | 标记已读 |
| `GET /api/realtime/stream` | SSE 实时推送（`?token=` 鉴权）：事件 `violation` / `warning` / `camera_status`，15s 心跳；前端 `composables/useRealtime.ts` 共享单连接，轮询仅作兜底 |
| `POST /api/warnings/email/test` | 预警邮件自检（SMTP 未配置时返回提示） |
| `GET/PUT /api/settings/mail`、`POST /api/settings/mail/test` | 邮件 SMTP 配置读写（密码脱敏，空值不修改）与测试发送；网页「预警中心 → 预警配置」使用 |
| `GET/PUT /api/settings/report`、`POST /api/settings/report/send?period=daily\|week\|month` | 报告推送配置（预警邮件开关/日报/周报/收件人）与立即发送 |
| `POST /api/logs/report/email?period=week\|month` | 生成报告 PDF 并邮件发送（看板导出下拉里的“邮件发送”） |

`violations` 表新增列 `anno_url`（标注证据图）、`detections_json`（帧内检测明细）；后端启动时 `_ensure_schema()` 自动 ALTER TABLE 补列（SQLite/MySQL 通用）。

**预警触发链路**：违规入库（`violations.py` / `demo.py` 两条路径）commit 后调用 `app/services/warnings.py::trigger_warning_check` —— 匹配启用规则 → 统计窗口内违规数 ≥ 阈值 → 生成 `warning_events`（同 camera+type 10 分钟冷却防刷屏）。预警规则/事件为新表，`create_all` 自动创建（`warning_rules`、`warning_events`）。生成事件后同时：① 通过 `services/events.py` 事件总线 SSE 推送；② 后台线程调用 `services/mailer.py` 发邮件（HTML 正文 + 该摄像头/类型最近一条抓拍图附件）。SMTP 配置见 `backend/.env.example`，也可在后台「预警中心 → 预警配置」网页修改（`system_settings` 表优先于 .env）；未配置 `SMTP_HOST/MAIL_TO` 时自动跳过。日报/周报由 `services/report_scheduler.py` 后台线程每 30 秒检查一次配置时间并发送，发送记录写入 `report.last_daily_sent` / `report.last_weekly_sent`。

**智慧大屏**：`/screen` 独立全屏路由（深色，1920×1080 等比缩放），支持 `?layout=overview|alerts`、`?rotate=秒` 值班轮播、`?present=1` 展厅模式；`deploy/start-screen.bat` 用 Chrome/Edge kiosk 全屏打开。视频轮巡（flv.js 宫格）为后续第二批。

### 违规判定模式（`judge.py`）

- `direct`（默认，适配 ppe.pt）：模型直接输出 `NO-*` 违规类，`rule: {"no_helmet": "NO-Hardhat", ...}`，出现即违规。
- `person_iou`（正类装备模型）：`rule: {"no_helmet": "helmet", ...}`，对每个 `person` 与装备框 IoU < 阈值判缺失。

### 火源火灾检测（第二模型，与 PPE 并行；全部摄像头同时检测）

系统在 PPE 检测基础上**并行运行独立的火源/烟雾 YOLO 模型**（`fire.pt`，2 类：`0=smoke` `1=fire`，YOLOv8n）。每个接入了的摄像头（正式链路）与演示页每一帧（演示链路）都**同时**做 PPE 与火源检测，违规类型新增 `fire`（火源火灾）/ `smoke`（烟雾），走 `direct` 判定（出现即违规），并复用现有抓拍/入库/预警/SSE/看板/大屏全链路：

| 位置 | 火源相关配置 |
|---|---|
| `inference/config.yaml` / `config.local.yaml` | `fire_enabled`、`fire_model_path`、`fire_class_names`、`fire_violation_rule`（`fire:fire`/`smoke:smoke`）、`fire_conf_threshold` |
| `backend/app/config.py` | `DEMO_FIRE_ENABLED`、`DEMO_FIRE_MODEL_PATH`、`DEMO_FIRE_CONF_THRESHOLD`、`FIRE_VIOLATION_RULE`；`VIOLATION_TYPES`/`VIOLATION_RULE` 已含 `fire`/`smoke` |
| `inference/stream_worker.py` | 每 worker 额外加载 `fire_detector`，与 PPE `detector` 并行 predict 后合并检测结果与违规 |
| `backend/app/routers/demo.py` | `get_fire_detector()` 懒加载第二检测器，`/api/demo/detect` 合并两模型结果 |
| `backend/app/detection/annotate.py`（与 inference 同步） | `FIRE_CLASSES`（橙色框 `ORANGE`）、`VIOLATION_LABELS` 加 `fire/smoke` |
| `frontend/src/constants/violations.ts` | `FIRE_CLASSES`（橙 `#ff7d00`）、`VIOLATION_TYPE_MAP` 加 `fire/smoke` |
| `frontend/src/utils/draw.ts` | 画布叠加：火源/烟雾橙色框，`onlyViolations` 也包含 fire/smoke |

火源模型权重 `weights/fire/fire.pt`（约 6 MB，来自公开 HF 模型 `rabahdev/fire-smoke-yolov8n`）。所有模型权重集中存放于仓库根目录 `weights/`（按用途分子目录：`weights/ppe/ppe.pt`、`weights/fire/fire.pt`，见 `weights/README.md`）。`*.pt` 不入库，克隆后需补放。docker 中 backend 与 inference 共用 `./weights:/app/weights` 挂载，`/app/weights/ppe/ppe.pt`、`/app/weights/fire/fire.pt` 自动可用。

### 模型类别与违规配置分布在多处（改模型时都要改）

| 位置 | 内容 |
|---|---|
| `inference/config.yaml` / `config.local.yaml` | `class_names`、`violation_rule`、`judge_mode`、`model_path`、`device` |
| `backend/app/config.py` | `VIOLATION_RULE`、`JUDGE_MODE`、`DEMO_MODEL_PATH`、`DEMO_CONF_THRESHOLD` |
| `backend/app/detection/annotate.py`（与 inference 同步） | 标注配色 `NEGATIVE_CLASSES` / `POSITIVE_CLASSES` + `VIOLATION_LABELS` 中文名 |
| `frontend/src/constants/violations.ts` | 统一常量：`VIOLATION_TYPE_MAP`、`NEGATIVE_CLASSES`、`POSITIVE_CLASSES`、`classColor`（各页面引用，勿在页面内重复定义） |
| `frontend/src/utils/draw.ts` | 画布检测框叠加绘制（演示页与监控页共用） |
| 根目录 `Safety-Detection*.py` | 硬编码 `classNames` 列表 |
| `frontend/.env` | `VITE_MEDIAMTX_BASE`（MediaMTX FLV 地址前缀，默认 `http://localhost:8080`，见 `.env.example`） |

后端默认配置：`JUDGE_MODE=direct`、SQLite、admin/admin123（硬编码在 `config.py`）、抓拍目录 `./images`（相对 backend 启动目录）。演示模型自动按候选路径搜索：`weights/ppe/ppe.pt`、`weights/fire/fire.pt`（docker 挂载 `/app/weights/` 或仓库内 `weights/` 等）。

### 技术栈要点

- **Python 依赖用 uv 管理**，各子项目有独立 `pyproject.toml`（backend / inference / 根目录三份）。PyTorch 通过 `[tool.uv.sources]` 固定到 `pytorch-cu132` 索引（有 NVIDIA GPU 时装 CUDA 版，无则回落 CPU）。
- **数据库**：`backend/app/database.py` 按 `DATABASE_URL` 是否 sqlite 区分引擎参数（SQLite 需 `check_same_thread=False`，MySQL 用连接池）。建表由 `Base.metadata.create_all` 在启动时自动完成（生产可用 `backend/init.sql`）。五张表：`cameras`、`violations`、`warning_rules`（预警规则）、`warning_events`（预警事件）、`system_settings`（邮件/报告配置键值）。
- **认证**：JWT（`security.py`），前端 `utils/request.ts` 拦截器自动附加 token，401 时跳转登录页。
- **Docker**：后端/inference 均用 `python:3.12-slim` + requirements.txt（非 pyproject）；前端 node 构建 + nginx 反代 `/api`、`/images` 到 backend。模型权重通过 volume 挂载。
- **流媒体**：`deploy/mediamtx.yml` 配置 RTSP 入 8554、HTTP 出 8080（FLV/WebRTC），浏览器经 flv.js 播放。

### 重要陷阱

- `*.pt` 不入库（.gitignore）：克隆后若缺模型，需补齐到 `weights/ppe/ppe.pt`（PPE）与 `weights/fire/fire.pt`（火源），或由后端演示模式自动搜索。
- 推理服务 cwd 必须是仓库根目录，否则 `python -m inference.main` 与相对路径配置失效。
- 所有模型权重集中存放于根目录 `weights/`（按用途分子目录，见 `weights/README.md`），配置/代码/docker 路径均指向此处。
- `frontend/public/camera-test.html` 是摄像头测试辅助页（静态文件）。
- 后端启动会预热演示模型（后台线程），首次 `/api/demo/detect` 才不卡顿；前端请求超时已放宽到 60s 以覆盖冷启动。
- **SQLite 时间戳陷阱**：SQLite 的 `CURRENT_TIMESTAMP`（`server_default`）存的是 **UTC**，与业务层本地时间比较会差 8 小时（预警窗口统计、今日统计都会错）。因此模型时间戳一律用 Python 侧 `default=datetime.now`（本地时间）写入，**不要**改回 `server_default=_func.now()`。存量 SQLite 库曾做一次性 +8h 迁移（仅本地开发库，MySQL 的 `now()` 本就是本地时间，无此问题）。
- reportlab（`/api/logs/report` PDF 导出）已加入 `backend/pyproject.toml` 与 `requirements.txt`；若 `uv sync` 因 ultralytics 解析失败（网络/索引问题，与本项目代码无关），可用 `uv pip install reportlab==4.2.5 --python ../.venv/Scripts/python.exe` 单独补装。
