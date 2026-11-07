# 架构参考：工地 AI 安全监测系统

> 本文是**开发者视角**的架构文档，讲清楚系统为什么这么设计、模块如何协作、改什么去哪里改。
> 面向初学者，建议先读系列博客第 1/5 篇建立直觉，再回来对照本文。
> 博客版讲解见 [05-系统架构与数据流-三链路解析.md](./05-系统架构与数据流-三链路解析.md)。

## What This Document Covers

本系统是一个 **"感知 → 判定 → 留痕 → 管理"** 的闭环：摄像头画面进来，AI 判定违规，违规自动抓拍留痕入库，后台管理看板把数据变成决策。

本文覆盖：系统组件划分、三条业务链路、关键设计决策（含权衡）、模块依赖、扩展点（新功能从哪下手）、部署架构。目标读者是**需要做较大改动**的开发者。

## System Design

### High-Level Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    推理服务 (inference/)                  │
                    │  main.py 拉取启用摄像头列表，每摄像头一个 StreamWorker 线程 │
                    │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
RTSP 摄像头 ───────▶│ StreamWorker │  │ StreamWorker│  │ StreamWorker│...     │
   (海康/大华)       │  拉流→检测   │  │  拉流→检测  │  │  拉流→检测  │          │
   │                 │  →判定→抓拍  │  │  →判定→抓拍 │  │  →判定→抓拍 │          │
   │                 └──────┬─────┘  └──────┬─────┘  └──────┬─────┘          │
   │                        │  违规(multipart)                │              │
   ▼                        ▼                                ▼              │
MediaMTX(8554)       ┌──────┴────────────────────────────────┴──────┐       │
   │ RTSP→FLV(8080)  │              FastAPI 后端 (backend/)           │       │
   ▼                 │  violations/with-image → 存图 + 入库 → 预警检查  │       │
flv.js 播放          │  demo/detect（演示模式，后端直接推理）            │       │
   ▲                 │  /images 静态目录 · /docs 接口文档              │       │
   │                 └──────────────┬──────────────────┬────────────┘       │
   │                                ▼                  ▼                     │
   │                        SQLite / MySQL        warning_rules 规则检查     │
   │                                                                         │
Vue3 前端 (frontend/) ◀────── /api + /images ──────▶  后端                  │
   │ 看板 / 监控 / 演示 / 违规记录 / 预警中心 / 日志导出                      │
   ▼                                                                         │
浏览器（Web 管理后台）                                                      │
```

**Components:**

1. **前端 `frontend/`**（Vue3 + TypeScript + Element Plus）— 管理后台与演示入口。消费后端 `/api`；监控页经 MediaMTX 的 FLV 流播放实时画面，叠加 AI 检测框。
2. **后端 `backend/`**（FastAPI + SQLAlchemy）— 业务核心：摄像头/违规/日志/预警的 CRUD 与聚合；同时充当"演示模式推理机"（独立加载模型，复同一套 detector/judge/annotate）。
3. **推理服务 `inference/`**（Python + OpenCV + Ultralytics）— 与后端解耦的独立进程：从后端拉取启用摄像头，每摄像头一个线程拉流检测，违规时抓拍并 multipart 上报。
4. **流媒体 `deploy/mediamtx.yml`**（MediaMTX）— 摄像头 RTSP 流的收转中心：入 8554，出 8080（FLV/WebRTC），前端靠它预览，推理服务靠它稳定拉流。
5. **数据库** — 四张表：`cameras`（设备）、`violations`（违规留痕）、`warning_rules` / `warning_events`（预警规则与事件）。本地 SQLite，Docker 用 MySQL。

### Technology Stack

| 层 | 技术 | 为什么选它 |
|---|---|---|
| 前端 | Vue3 + Element Plus + TypeScript + Vite | 组合式 API 上手快；Element Plus 后台组件齐全；TS 提供编译期类型检查（vue-tsc）；Vite 开发热更新快 |
| 前端图表 | ECharts（按需引入） | 看板趋势/分布/排行；按需引入把打包体积 1.1MB → 560KB |
| 前端流媒体 | flv.js | MediaMTX 输出 FLV，浏览器直接播放 RTSP 转发的流 |
| 后端 | FastAPI + SQLAlchemy | 自动 Swagger 文档（`/docs`）；异步 + 线程池适配推理阻塞；ORM 屏蔽 SQLite/MySQL 差异 |
| 数据库 | SQLite（本地）/ MySQL 8.0（Docker） | 本地零依赖可跑；生产容器化用 MySQL |
| 推理 | Ultralytics YOLOv8 + OpenCV | 一阶段检测器，实时性满足视频流；Ultralytics 生态开箱即用；OpenCV 负责拉流与画框 |
| 流媒体 | MediaMTX | 轻量单二进制，RTSP→FLV/WebRTC 一键转发 |
| 报告 | reportlab 4.2.5 + pandas/openpyxl | PDF 周报/月报（内置 STSong-Light 中文字体）；Excel 导出内嵌违规图片 |
| 部署 | Docker + Compose | 后端/inference 用 python:3.12-slim，前端 node 构建 + nginx 反代 |

## Directory Structure

```
├── backend/app/                 # 后端业务
│   ├── main.py                  # 入口：建表 → _ensure_schema 补列 → 静态目录 → CORS → 模型预热 → 路由注册
│   ├── config.py                # 全部配置（pydantic-settings，.env 可覆盖）
│   ├── database.py              # 引擎（SQLite check_same_thread / MySQL 连接池）+ get_db
│   ├── models.py                # 四张表 ORM（时间戳一律 default=datetime.now 本地时间）
│   ├── schemas.py               # 请求/响应模型（FastAPI 校验 + Swagger 生成）
│   ├── security.py              # JWT 签发（HS256，当前未强制校验）
│   ├── detection/               # detector/judge/annotate —— 与 inference/ 逐行一致（双份同步）
│   ├── routers/                 # auth / cameras / violations / logs / demo / warnings
│   └── services/warnings.py     # 预警触发三层逻辑（冷却 → 规则匹配 → 窗口统计）
├── inference/                   # 推理服务（独立进程）
│   ├── main.py                  # 拉取启用摄像头，每路启动 StreamWorker
│   ├── stream_worker.py         # 线程循环：拉流 → 每N帧检测 → 判定 → 去重抓拍 → 上报 + 心跳
│   ├── detector.py / judge.py / annotate.py   # 与 backend 双份同步
│   └── config.yaml / config.local.yaml
├── frontend/src/
│   ├── constants/violations.ts  # 违规中文名 + 配色唯一来源（跨页面共享）
│   ├── utils/draw.ts            # canvas 检测框叠加（演示/监控页共用）
│   ├── utils/request.ts         # axios 封装（token 拦截器 / 401 跳登录 / 60s 超时）
│   └── views/                   # 8 个页面
└── deploy/mediamtx.yml          # 流媒体配置
```

## Data Flow

### 链路一：正式链路（RTSP 摄像头 → 违规入库）

```
摄像头帧 → [StreamWorker 线程] detector.predict()  → List[Detection]
       → judge_violations()（direct: 出现 NO-* 即违规）
       → 违规时 draw_annotations() 画证据图
       → _report()：dedup_seconds 去重 → 存原始帧+标注图 → multipart POST /api/violations/with-image
       → 后端存图（/images）+ violations 入库 + trigger_warning_check()
```

**Step-by-step:**

1. **启动**：`inference/main.py` 调 `GET /api/cameras` 拉取启用摄像头列表（`enabled=true`），每摄像头起一个 `StreamWorker` 线程；无启用摄像头时服务直接退出。
2. **循环**：`stream_worker.run()` 用 OpenCV 拉流，每 `detect_interval` 帧做一次检测（降负载），断流自动重连。
3. **判定**：`judge_violations()` 返回违规 key 集合（`no_helmet` 等）。
4. **去重 + 抓拍**：命中且距上次上报超过 `dedup_seconds` 才上报，防刷屏；抓拍存原始帧 + 标注证据图。
5. **上报**：multipart POST `/api/violations/with-image`（字段：`file` 原始帧、`anno` 标注图、`detections` 帧内检测明细 JSON、`camera_id/camera_name/violation_type/confidence`）。
6. **入库 + 预警**：后端 `_ensure_schema` 已保证 `anno_url`/`detections_json` 列存在；commit 后调 `trigger_warning_check`。

### 链路二：演示链路（笔记本摄像头，后端直接推理）

```
浏览器 getUserMedia 取帧 → 每 500ms 截帧 POST /api/demo/detect（multipart file）
  → 后端 get_detector()（懒加载单例 + 双重检查锁）→ run_in_threadpool 推理（不阻塞事件循环）
  → judge_violations() 判定
  → 违规时（no_save=false）：抓拍存图 + 入库（camera_id=0, camera_name="临时演示"）+ 预警检查
  → 返回 detections[] + violations[] + snapshot_url（标注证据图）
  → 前端 drawDetections() 叠加画框 + 统计面板 + 抓拍时间线
```

**复用设计的关键**：演示链路与正式链路共用 `detector/judge/annotate`（双份同步），判定逻辑完全一致；监控页 AI 叠加也复用本接口（`no_save=true` 只检测不入库）。

### 链路三：预警链（违规 → 预警事件 → 铃铛提醒）

```
违规入库（violations.py / demo.py 两条路径）commit 后
  → trigger_warning_check(db, camera_id, camera_name, violation_type)
  → ① 10 分钟冷却检查（同 camera+type 冷却期内直接返回）
  → ② 规则匹配（enabled=true，camera_id/type 空=通配）
  → ③ 窗口统计（最近 window_minutes 分钟该摄像头该类型违规数 ≥ threshold）
  → 生成 warning_events + commit
  → 前端顶栏每 10s 轮询 /api/warnings/unread-count → 未读徽标 + 弹窗
```

### State Management（前端）

前端状态管理极简：无 Pinia/Vuex。路由守卫读 `localStorage.token`，页面数据各自在组件内拉接口管理。跨页面的"业务常量"（违规中文名/配色）集中在 `constants/violations.ts`，页面内不重复定义。

## Key Design Decisions

### 决策 1：违规判定用 direct 模式（ppe.pt 直接输出违规类）

**What we decided:** 默认 `judge_mode="direct"`，模型输出 `NO-*` 违规类，出现即判违规；同时保留 `person_iou` 模式（正类装备 + IoU）。

**Context:** 仓库原有多套代码/配置，需适配根目录 `ppe.pt`（10 类违规模型）。direct 模式下判定逻辑只有三行集合运算，无需后处理。

**Why we decided this:**
- **判定简单可靠**：`return {vio for vio, cls in rule.items() if cls in names}`——出错面小；
- **适配工作量最小**：ppe.pt 正好是违规类输出，direct 是"为它量身定制"的模式；
- **person_iou 兜底通用性**：换成正类装备模型时，`judge_mode` 一改即可，代码路径已保留。

**Trade-offs:**
- ✅ 简单、快、易维护
- ❌ 依赖模型本身能输出违规类（换通用模型必须切 person_iou）
- 🤔 **何时重新考虑：** 换成只输出正类装备（person/helmet）的模型时，必须同步改 5 处配置（见 README 任务 4）

**Alternatives considered:**
- 后处理 IoU（person_iou）：通用但对每个 person 都要算 IoU，且需要正类装备检测可靠；保留为模式二而非默认。

### 决策 2：双份同步（inference/ 与 backend/app/detection/ 逐行一致）

**What we decided:** `detector.py / judge.py / annotate.py` 在 `inference/` 与 `backend/app/detection/` **各存一份、逐行一致**；改动必须同步。

**Context:** 演示模式由后端独立加载模型推理，不能跨进程调用推理服务；为复用同一套检测/判定/标注逻辑，把文件复制到了后端。

**Why we decided this:**
- 演示链路与正式链路**判定结果一致**（客户演示看到的就是正式链路的逻辑）；
- 避免"后端再写一套"造成的逻辑漂移。

**Trade-offs:**
- ✅ 逻辑一致、后端零网络依赖
- ❌ **双份维护成本高**——改一处忘另一处就会出现两链路不一致（本项目真实踩过）
- 🤔 **何时重新考虑：** 抽出公共 Python 包（`pip install` 一份）即可彻底解决，代价是引入包发布/版本管理

### 决策 3：本地 SQLite 优先，Docker 再切 MySQL

**What we decided:** `DATABASE_URL` 默认 `sqlite:///./yolo_safety.db`，docker-compose 用环境变量覆盖为 MySQL。

**Context:** 目标用户是学生/演示场景，本地要"开箱即跑"；生产/竞赛演示走 Docker。

**Why we decided this:**
- SQLite 零依赖、自动建表，`uv run uvicorn` 一条命令跑通全链路；
- 通过 `DATABASE_URL` 一个变量切换数据库，ORM 屏蔽差异（引擎参数在 `database.py` 分支处理）。

**Trade-offs:**
- ✅ 本地体验极佳、无 MySQL 门槛
- ❌ 两个数据库时间函数语义不同（SQLite `CURRENT_TIMESTAMP`=UTC，MySQL `NOW()`=本地）——本项目的最大坑（见决策 5）
- 🤔 **何时重新考虑：** 生产规模 / 多并发写 / 需要迁移工具时，应引入 Alembic 并固定 MySQL

### 决策 4：演示模式由后端加载模型，而不是调推理服务

**What we decided:** `backend/app/routers/demo.py` 懒加载 `YoloDetector` 单例（双重检查锁），`run_in_threadpool` 推理；启动时后台线程预热模型。

**Context:** 演示链路要从浏览器取帧检测，若调推理服务需要：推理服务常驻 + 内部接口。为把演示做成"后端开箱即用"，直接在后端推理。

**Why we decided this:**
- 演示不依赖推理服务进程（不用先录摄像头/起推理服务）；
- 单例 + 预热避免首次请求卡 10~30s；
- `run_in_threadpool` 让推理不阻塞事件循环（并发时登录/心跳仍可响应）。

**Trade-offs:**
- ✅ 演示链路零依赖、响应快
- ❌ 后端进程要扛推理负载（与推理服务职责重叠）；模型加载失败只在接口层返回 503
- 🤔 **何时重新考虑：** 多用户并发演示 / 生产级负载时，应把推理收归推理服务，后端只做编排

### 决策 5：时间戳用 Python 本地时间写入（SQLite 陷阱）

**What we decided:** 模型时间戳一律 `default=datetime.now`（Python 侧，本地时间），**不用** `server_default=_func.now()`。

**Context:** 阶段四实现预警后发现窗口统计永远为 0——SQLite 的 `CURRENT_TIMESTAMP` 存 **UTC**，与本地时间（UTC+8）比较差 8 小时。存量数据做了 +8h 一次性迁移。

**Why we decided this:**
- 业务层（`datetime.now()`）与存储层口径一致，预警/今日统计不再出错；
- MySQL 的 `NOW()` 本就是本地时间，同一写法跨库安全。

**Trade-offs:**
- ✅ 简单、跨库一致、可排障
- ❌ 牺牲"统一 UTC 存储"的规范做法（跨时区部署时会再次遇到）
- 🤔 **何时重新考虑：** 多时区部署 / 数据要对外交换时，应改回 UTC 存储 + 展示层转换（需配套迁移）

### 决策 6：预警触发时机放在"违规入库 commit 之后"

**What we decided:** `trigger_warning_check` 在 `violations.py` / `demo.py` 的 `db.commit()` **之后**调用；预警逻辑独立成 `services/warnings.py`。

**Context:** 窗口统计需要"包含刚入库的这条记录"，commit 前统计永远"差一条才触发"。

**Why we decided this:**
- 统计口径正确（注释明确写了"commit 后统计，需包含刚入库记录"）；
- 业务解耦：违规入库处只调一行函数，预警方不依赖入库流程，入库方不感知预警细节。

**Trade-offs:**
- ✅ 语义正确、耦合低
- ❌ 预警逻辑在请求线程内同步执行（规则多/数据量大时会拖慢入库响应）
- 🤔 **何时重新考虑：** 高吞吐时改消息队列/异步任务触发

### 决策 7：PDF 趋势图用 shapes 手绘（reportlab 4.2 重构）

**What we decided:** `_build_trend_chart` 用 reportlab shapes 原语（Line/PolyLine/Circle/String）手绘趋势图，且 `reportlab==4.2.5` 锁版本。

**Context:** reportlab 4.2 重构图表库，`LineChart` 的经典 `data` API 失效（MRO 变为 AbstractLineChart→PlotArea→Widget），老代码报 `Illegal attribute 'data'`。

**Why we decided this:**
- shapes 原语 API 稳定，不随 charts 组件演进破坏；
- 手绘还能自由控制标签密度（30 天只显示约 8 个日期标签）。

**Trade-offs:**
- ✅ 稳定、可控
- ❌ 复杂图表（如多序列）手绘成本高
- 🤔 **何时重新考虑：** 需要复杂图表时换 matplotlib/plotly 生成图片再嵌入

## Module Dependencies

```
backend/
  main.py ──→ routers/* ──→ services/warnings.py
              ├── routers/demo.py ──→ detection/(detector/judge/annotate) ──→ config.py
              └── routers/logs.py ──→ models.py · detection/annotate(VIOLATION_LABELS)
  models.py · schemas.py · security.py ──→ config.py

inference/
  main.py ──→ stream_worker.py ──→ detector.py / judge.py / annotate.py / config.yaml
  stream_worker.py ──(POST /api/violations/with-image)──→ backend

frontend/
  views/* ──→ api/* ──→ utils/request.ts
  views/monitor · views/demo ──→ utils/draw.ts ──→ constants/violations.ts
```

**依赖规则：**

1. **共享常量单向依赖**：`views/*` → `constants/violations.ts`（页面不反向定义，改模型/配色只改一处）；
2. **前后端"双份同步"是显式约定**：`backend/app/detection/` ↔ `inference/` 对应文件内容一致，靠 CLAUDE.md 与代码头注释约束（非代码依赖，靠纪律）；
3. **避免循环依赖**：`services/warnings.py` 只依赖 models，不反向依赖 routers；`routers/demo.py` 的检测器单例在模块内持有，不依赖其他 router。

### External Dependencies

| 包/组件 | 用途 | 备注 |
|---|---|---|
| ultralytics | YOLO 加载与推理 | PyTorch 经 uv source 固定 CUDA 索引 |
| opencv-python | 拉流/解码/画框 | annotate.py 画检测框用 |
| fastapi / uvicorn | Web 框架 | 自动 Swagger |
| sqlalchemy | ORM | 双库引擎 |
| reportlab 4.2.5 | PDF 报告 | 锁版本，STSong-Light CID 中文 |
| pandas + openpyxl | Excel 导出 | 无则 CSV 兜底 |
| vue / element-plus / echarts / flv.js | 前端 | ECharts 按需引入 |
| mediamtx | 流媒体 | RTSP→FLV |

## Extension Points

### 新增一个违规类型（如"未系帽带"）

1. **模型侧**：训练/替换模型，确认输出新类别名；
2. **配置**：`inference/config.yaml` + `backend/app/config.py` 的 `VIOLATION_RULE` / `class_names` 增加条目；
3. **中文/配色**：双份 `annotate.py` 的 `VIOLATION_LABELS` + 前端 `constants/violations.ts` 的 `VIOLATION_TYPE_MAP` / `NEGATIVE_CLASSES`；
4. **预警**：预警规则页已支持任意 `violation_type`（空=全部），无需改代码；
5. **报表**：PDF 报告自动带新类型（读 `VIOLATION_LABELS`）。

**验证：** `YOLO(path).names` 比对；演示一次看是否标红 + 入库。

### 新增一个后端接口

1. `backend/app/routers/` 下新文件或新增路由函数；
2. `schemas.py` 定义请求/响应模型（自动进 Swagger）；
3. `main.py` 注册 `app.include_router(..., prefix="/api/xxx")`；
4. 前端 `src/api/xxx.ts` 封装 + `views/` 页面消费；
5. 验证：`vue-tsc` + `vite build`；后端实跑实测贴响应。

### 新增一张数据库表

1. `models.py` 定义 ORM 模型（时间戳用 `default=datetime.now`，别用 `server_default`）；
2. `Base.metadata.create_all` 启动时自动建新表；**老表加列**需走 `main.py` 的 `_ensure_schema` 模式（幂等 ALTER）或引入 Alembic；
3. `schemas.py` 加对应 Pydantic 模型，`routers/` 加 CRUD。

### 新增一种检测能力（如"危险区域入侵"）

- 画面划禁区，person 框与禁区 IoU 判定——可在 `judge.py` 加新判定模式，或在前端划区 + 上报区域坐标；
- 复用 `annotate.py` 画禁区框 + `warning` 链路（新 violation_type）。

## Deployment Architecture

| 环境 | 启动方式 | 数据库 | 备注 |
|---|---|---|---|
| 本地开发 | `start-local.bat` / 三个终端 | SQLite | 推理服务需手动取消注释启用 |
| Docker | `docker compose up -d --build` | MySQL（env 覆盖） | 前端 nginx 反代 /api、/images；模型 volume 挂载 |

**构建产物：** 前端 `npm run build` → dist，nginx 托管并反代后端；后端/inference 用 `python:3.12-slim` + requirements.txt（非 pyproject）。

**部署步骤（Docker）：**
1. `inference/weights/ppe.pt` 存在（volume 挂载）；
2. `docker compose up -d --build`；
3. 浏览器访问 `http://localhost`，后端 `/docs`。

## Troubleshooting（架构层面）

**Issue: 演示与正式链路标注不一致**
- **Symptoms：** 同一条违规，演示页横幅和违规记录标注图中文/颜色不同
- **Cause：** 双份 `annotate.py` 只改了一处
- **Solution：** 全仓库搜索 `VIOLATION_LABELS` / `NEGATIVE_CLASSES`，确认 `inference/` 与 `backend/app/detection/` 一致

**Issue: 推理服务启动即退出**
- **Symptoms：** 无报错直接退出
- **Cause：** 无启用摄像头（`fetch_cameras` 返回空）
- **Solution：** 先在后端录入摄像头并开启 enabled；确认 cwd 是仓库根目录

**Issue: 看板/预警统计异常**
- **Symptoms：** 今日数不对 / 预警不触发 / 趋势断档
- **Cause：** 时间戳存 UTC 与本地比较差 8 小时；或趋势未补零
- **Solution：** 查 `violations.created_at` 是否差 8h；确认模型时间戳为 Python 本地时间（见决策 5）

## Additional Resources

- 博客导读：[doc/README.md](./README.md)
- 全接口参考：[doc/API接口参考.md](./API接口参考.md)
- 后端实战：[06-后端实战-FastAPI与数据模型.md](./06-后端实战-FastAPI与数据模型.md)
- 推理实战：[07-推理实战-YOLOv8检测判定与抓拍.md](./07-推理实战-YOLOv8检测判定与抓拍.md)
- 前端实战：[08-前端实战-Vue3后台管理系统.md](./08-前端实战-Vue3后台管理系统.md)
- 数据驱动（看板/PDF/预警/时间戳坑）：[09-数据驱动-看板PDF预警与工程陷阱.md](./09-数据驱动-看板PDF预警与工程陷阱.md)
