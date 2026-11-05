# 工地AI安全智能监测系统（YOLO版）

基于 **YOLO 目标识别** 的工地安全帽 / 马甲 / 口罩智能监测后台管理系统。

自动对接主流监控摄像头（海康 / 大华等，RTSP 协议），实时识别不规范穿戴行为，**违规自动抓拍留痕**、**入库生成安全日志**，并提供**前后端一体化的可视化后台管理**。

## ✨ 核心功能

- **监控设备对接**：兼容主流摄像头 RTSP 流，MediaMTX 转发，后台实时预览
- **AI 智能识别**：基于 YOLOv8，识别未戴安全帽 / 未穿马甲 / 未戴口罩
- **自动抓拍留痕**：违规瞬间自动截帧保存图片，杜绝人工干预
- **安全日志管理**：自动生成违规时间 / 点位 / 类型 / 置信度日志，支持筛选与 **Excel 导出**
- **Web 后台管理**：数据看板、摄像头管理、实时监控、违规记录、日志导出

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
│   │   └── routers/         # 认证 / 摄像头 / 违规 / 日志
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

## 📝 License

仅供学习与毕设/竞赛演示使用。
