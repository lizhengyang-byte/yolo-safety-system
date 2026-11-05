# 工地AI安全智能监测系统（YOLO版）

基于 **YOLO 目标识别** 的工地安全帽 / 马甲 / 口罩智能监测后台管理系统。

自动对接主流监控摄像头（海康 / 大华等，RTSP 协议），实时识别不规范穿戴行为，**违规自动抓拍留痕**、**入库生成安全日志**，并提供**前后端一体化的可视化后台管理**。

## ✨ 核心功能

- **监控设备对接**：兼容主流摄像头 RTSP 流，MediaMTX 转发，后台实时预览
- **AI 智能识别**：基于 YOLOv8，识别未戴安全帽 / 未穿马甲 / 未戴口罩
- **自动抓拍留痕**：违规瞬间自动截帧保存图片，杜绝人工干预
- **安全日志管理**：自动生成违规时间 / 点位 / 类型 / 置信度日志，支持筛选与 **Excel 导出**
- **Web 后台管理**：数据看板、摄像头管理、实时监控、违规记录、日志导出
- **临时演示模式**：直接调用笔记本摄像头（内置/外接 USB），实时 YOLO 识别 + 违规抓拍，无需接监控设备，适合现场演示

## 🏗️ 技术栈

| 模块 | 技术 |
|---|---|
| 前端 | Vue3 + Element Plus + TypeScript + Vite |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | MySQL 8.0 |
| 推理 | Ultralytics YOLOv8 + OpenCV |
| 流媒体 | MediaMTX（RTSP → FLV/WebRTC）|
| 部署 | Docker + Docker Compose |

## 📁 项目结构

```
yolo-safety-system/
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 配置
│   │   ├── models.py        # ORM 模型（Camera / Violation）
│   │   ├── security.py      # JWT 认证
│   │   ├── detection/       # 演示模式检测模块（复用推理逻辑）
│   │   └── routers/         # 认证 / 摄像头 / 违规 / 日志 / 演示
│   ├── requirements.txt
│   ├── init.sql             # 建库建表
│   └── Dockerfile
├── inference/          # YOLO 推理服务
│   ├── detector.py          # YOLO 封装
│   ├── judge.py             # 违规判定（IoU）
│   ├── stream_worker.py     # RTSP 拉流 + 抓拍 + 上报
│   ├── main.py              # 多摄像头并发入口
│   ├── config.yaml          # 模型类别 / 阈值等配置
│   └── Dockerfile
├── frontend/           # Vue3 前端
│   ├── src/
│   │   ├── api/             # 接口封装
│   │   ├── views/           # 看板/监控/摄像头/违规/日志页面
│   │   ├── layout/          # 主布局
│   │   └── router/          # 路由
│   ├── Dockerfile
│   └── nginx.conf
├── deploy/mediamtx.yml # 流媒体配置
├── docker-compose.yml
└── README.md
```

## 🚀 快速启动（Docker 一键部署）

### 前置条件
- Docker + Docker Compose
- 已训练好的 YOLO 权重 `best.pt`（放入 `inference/weights/`）

### 步骤
```bash
# 1. 放入模型权重
mkdir -p inference/weights
cp /path/to/your/best.pt inference/weights/

# 2. 按需修改推理类别配置
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

### 后端
```bash
cd backend
pip install -r requirements.txt
# 修改 config.py 中 DATABASE_URL 为本地 MySQL
uvicorn app.main:app --reload
```

### YOLO 推理服务
```bash
cd inference
pip install -r requirements.txt
# 启动 MySQL 和后端后，配置 config.yaml 指向后端地址
python -m inference.main
```

### 前端
```bash
cd frontend
npm install
npm run dev   # 已配置 /api 代理到 localhost:8000
```

## 🔧 需要按你的模型调整的地方

1. **`inference/config.yaml` 的 `class_names`**
   必须与你训练数据集 `data.yaml` 的类别顺序一致，例如：
   ```yaml
   class_names:
     0: person
     1: helmet
     2: vest
     3: mask
   ```
2. **违规判定规则 `violation_rule`**：定义"哪类违规缺少哪个装备"
3. **前端 `views/monitor/index.vue` 的 MediaMTX 播放地址模板**
4. **后端 `config.py`**：JWT 密钥、管理员账号、数据库地址

## 📄 数据库表

- `cameras`：监控摄像头设备（名称 / 点位 / RTSP地址 / 状态）
- `violations`：违规抓拍记录（类型 / 置信度 / 图片 / 时间）

## 🧩 架构流程

```
主流监控摄像头(RTSP)
   → MediaMTX 流媒体转发（前端预览 + 稳定拉流）
   → Python 拉流脚本(OpenCV)
   → YOLOv8 检测
   → 违规判定(IoU)
   → 自动抓拍截图
   → FastAPI 上报入库
   → MySQL 存储安全日志
   → Vue3 后台管理展示 / 导出
```

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
- 后端演示接口需能加载 `best.pt`（docker-compose 已把 `inference/weights` 挂载给 backend）
- 演示检测复用 `inference/detector.py` + `judge.py` 同一套逻辑，保证与正式链路识别一致

## 📝 License

仅供学习与毕设/竞赛演示使用。
