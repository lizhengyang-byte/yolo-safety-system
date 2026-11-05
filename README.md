# 工地AI安全智能监测系统（YOLO版）

基于 **YOLO 目标识别** 的工地安全帽 / 马甲 / 口罩智能监测后台管理系统。

自动对接主流监控摄像头（海康 / 大华等，RTSP 协议），实时识别不规范穿戴行为，**违规自动抓拍留痕**、**入库生成安全日志**，并提供**前后端一体化的可视化后台管理**。仓库同时保留原始 **Safety-Detection-YOLOv8 视频检测脚本**（见下文）。

> ⚠️ **适配说明（本仓库已适配 `ppe.pt` 模型）**
> 本仓库已适配根目录的 `ppe.pt` 模型（10 类，直接输出违规类）：
> - 类别顺序 `0 Hardhat, 1 Mask, 2 NO-Hardhat, 3 NO-Mask, 4 NO-Safety Vest, 5 Person, 6 Safety Cone, 7 Safety Vest, 8 machinery, 9 vehicle`
> - 违规判定为 **direct 模式**（出现 `NO-*` 类即判违规，无需 IoU），`inference/judge.py` 与 `backend/app/detection/judge.py` 同时支持 `person_iou` 通用模式（正类装备模型）
> - 后端演示模式会自动搜索模型路径（Docker 与本地均可用）
> - 后端默认使用 **SQLite**（本地零依赖可跑），Docker 部署时由环境变量覆盖为 MySQL

## ✨ 核心功能

- **监控设备对接**：兼容主流摄像头 RTSP 流，MediaMTX 转发，后台实时预览
- **AI 智能识别**：基于 YOLOv8，识别未戴安全帽 / 未穿马甲 / 未戴口罩
- **自动抓拍留痕**：违规瞬间自动截帧保存图片，杜绝人工干预
- **安全日志管理**：自动生成违规时间 / 点位 / 类型 / 置信度日志，支持筛选与 **Excel 导出**
- **Web 后台管理**：数据看板、摄像头管理、实时监控、违规记录、日志导出
- **临时演示模式**：直接调用笔记本摄像头（内置/外接 USB），实时 YOLO 识别 + 违规抓拍，无需接监控设备，适合现场演示
- **视频文件检测脚本**：对本地视频文件进行 PPE 检测并导出标注视频（CPU / GPU）

## 🏗️ 技术栈

| 模块 | 技术 |
|---|---|
| 前端 | Vue3 + Element Plus + TypeScript + Vite |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | MySQL 8.0（Docker）/ SQLite（本地开发） |
| 推理 | Ultralytics YOLOv8 + OpenCV |
| 流媒体 | MediaMTX（RTSP → FLV/WebRTC） |
| 部署 | Docker + Docker Compose |
| 脚本 | Python 3.12 + uv + cvzone |

## 📁 项目结构

```
yolo-safety-system/
├── backend/             # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 配置（SQLite 默认 / MySQL 可覆盖）
│   │   ├── models.py        # ORM 模型（Camera / Violation）
│   │   ├── security.py      # JWT 认证
│   │   ├── detection/       # 演示模式检测模块（复用推理逻辑）
│   │   └── routers/         # 认证 / 摄像头 / 违规 / 日志 / 演示
│   ├── pyproject.toml       # uv 工程配置
│   ├── requirements.txt
│   ├── init.sql             # 建库建表
│   └── Dockerfile
├── inference/           # YOLO 推理服务
│   ├── detector.py          # YOLO 封装
│   ├── judge.py             # 违规判定（direct / person_iou）
│   ├── stream_worker.py     # RTSP 拉流 + 抓拍 + 上报
│   ├── main.py              # 多摄像头并发入口
│   ├── config.yaml          # Docker 配置
│   ├── config.local.yaml    # 本地开发配置
│   ├── weights/             # 模型权重（ppe.pt，不入库）
│   ├── pyproject.toml       # uv 工程配置
│   └── Dockerfile
├── frontend/            # Vue3 前端
│   ├── src/
│   │   ├── api/             # 接口封装
│   │   ├── views/           # 看板/监控/摄像头/违规/日志/演示页面
│   │   ├── layout/          # 主布局
│   │   └── router/          # 路由
│   ├── Dockerfile
│   └── nginx.conf
├── deploy/mediamtx.yml  # 流媒体配置
├── Safety-Detection.py          # 原始脚本：实时窗口检测
├── Safety-Detection-export.py   # 原始脚本：视频导出（CPU）
├── Safety-Detection-export-gpu.py  # 原始脚本：视频导出（GPU）
├── pyproject.toml / uv.lock     # 原始脚本依赖（uv 管理）
├── docker-compose.yml
└── README.md
```

## 🚀 快速启动（Docker 一键部署）

### 前置条件
- Docker + Docker Compose
- 模型权重 `ppe.pt`：放入 `inference/weights/ppe.pt`（若克隆仓库后缺失，从根目录复制一份即可）

### 步骤
```bash
# 1. 确认模型权重存在
ls inference/weights/ppe.pt

# 2. 按需修改推理类别配置（当前已适配 ppe.pt 的 10 类）
vim inference/config.yaml

# 3. 一键启动全部服务
docker compose up -d --build
```

### 访问地址
| 服务 | 地址 |
|---|---|
| 前端后台 | http://localhost |
| 后端接口文档 | http://localhost:8000/docs |
| 抓拍图片 | http://localhost:8000/images/xxx.jpg |
| MediaMTX FLV | http://localhost:8080/live/{id}.flv |

### 默认账号
```
用户名：admin
密码：admin123
```

## 🛠️ 本地开发（不使用 Docker）

已适配当前项目工具链（uv + Python 3.12），后端默认 SQLite，**无需 MySQL** 即可完整运行。

### 后端
```bash
cd backend
uv sync                     # 或 pip install -r requirements.txt
uv run uvicorn app.main:app --reload   # 默认 SQLite 数据库 yolo_safety.db，自动建表
```
- 演示模型自动搜索 `../inference/weights/ppe.pt` / `inference/weights/ppe.pt` / 根目录 `ppe.pt` 等路径，无需配置
- 如需 MySQL：`DATABASE_URL=mysql+pymysql://root:yolo123456@127.0.0.1:3306/yolo_safety?charset=utf8mb4 uv run uvicorn app.main:app --reload`

### YOLO 推理服务
```bash
cd inference
uv sync                     # 或 pip install -r requirements.txt
# 注意：推理服务必须从仓库根目录启动（inference 是包名），
# 本地配置已提供（backend_url 指向 localhost），启动后端后：
cd ..
CONFIG_PATH=inference/config.local.yaml uv run python -m inference.main
```

### 前端
```bash
cd frontend
npm install
npm run dev   # 已配置 /api 与 /images 代理到 localhost:8000，访问 http://localhost:3000
```

## 🎬 原始脚本：视频文件 PPE 检测

根目录三个脚本用于对本地视频做 PPE 检测并导出标注视频（与系统共用 `ppe.pt`）。

```bash
# 依赖（根目录 pyproject.toml，uv 管理）
uv sync

# 实时窗口播放检测（默认打开 videos/ 下视频，可修改脚本内路径）
uv run python Safety-Detection.py

# 导出带标注的视频（CPU，可指定输入/输出）
uv run python Safety-Detection-export.py --input videos/xxx.mp4 --output videos/xxx_out.mp4

# GPU 加速导出（自动检测 CUDA，可选 --half 半精度；无 GPU 自动回落 CPU）
uv run python Safety-Detection-export-gpu.py --input videos/xxx.mp4 --output videos/xxx_out.mp4 --half
```

标注配色：红色 = 违规（未戴安全帽/未戴口罩/未穿马甲），绿色 = 合规穿戴，蓝色 = 其他目标（人/锥桶/机械/车辆）。

## 🎥 临时演示模式（笔记本摄像头）

无需对接 RTSP 监控设备，直接调用笔记本内置/外接 USB 摄像头实时演示，**流程与正式链路完全一致**（检测→判定→抓拍入库）。

### 演示流程
```
笔记本摄像头(浏览器 getUserMedia)
   → 前端截帧上传 /api/demo/detect
   → 后端 YOLO 检测 + 违规判定
   → 违规自动抓拍入库（camera_id=0, 来源"临时演示"）
   → 前端叠加绘制检测框/违规标签 + 展示最近抓拍
```

### 使用步骤
1. 登录后台 → 左侧菜单点「**临时演示**」
2. 选择摄像头（内置/外接 USB，可切换）
3. 点「**开始演示**」→ 授权浏览器摄像头权限
4. 画面实时叠加检测框，违规时标红并显示提示，最近抓拍自动入库
5. 可在「违规记录」「安全日志」页看到演示产生的记录（来源为"临时演示"）

### 说明
- 浏览器调用摄像头需 **HTTPS 或 localhost** 环境
- 后端演示接口自动搜索 `ppe.pt`（`inference/weights/` 或仓库根目录）
- 演示检测复用 `inference/detector.py` + `judge.py` 同一套逻辑，保证与正式链路识别一致

## 🔧 需要按你的模型调整的地方

当前已适配 `ppe.pt`（10 类、direct 违规判定），若更换为其他模型需注意：

1. **`inference/config.yaml` 的 `class_names`**
   必须与模型实际类别顺序一致（可用 `YOLO(path).names` 查看）。ppe.pt 的配置：
   ```yaml
   class_names:
     0: Hardhat
     1: Mask
     2: NO-Hardhat
     3: NO-Mask
     4: NO-Safety Vest
     5: Person
     6: Safety Cone
     7: Safety Vest
     8: machinery
     9: vehicle
   ```
2. **违规判定规则 `violation_rule` + `judge_mode`**
   - `direct`（ppe.pt）：模型直接输出违规类，`rule` 值为 `NO-*` 类名
   - `person_iou`（正类装备模型，如 person/helmet/vest/mask）：`rule` 值为装备类名，
     后端 `config.py` 的 `JUDGE_MODE` 需同步改为 `person_iou`
3. **前端 `views/demo/index.vue` 的检测框配色常量**（`NEGATIVE_CLASSES` / `POSITIVE_CLASSES`）
4. **前端 `views/monitor/index.vue` 的 MediaMTX 播放地址模板**
5. **后端 `config.py`**：JWT 密钥、管理员账号、数据库地址

## 📄 数据库表

- `cameras`：监控摄像头设备（名称 / 点位 / RTSP地址 / 状态）
- `violations`：违规抓拍记录（类型 / 置信度 / 图片 / 时间）

## 🧩 架构流程

```
主流监控摄像头(RTSP)
   → MediaMTX 流媒体转发（前端预览 + 稳定拉流）
   → Python 拉流脚本(OpenCV)
   → YOLOv8 检测
   → 违规判定(IoU / direct)
   → 自动抓拍截图
   → FastAPI 上报入库
   → MySQL/SQLite 存储安全日志
   → Vue3 后台管理展示 / 导出
```

## 📝 License

MIT License，仅供学习与毕设/竞赛演示使用。
