# 模型权重集中目录

本目录集中存放所有模型权重，按用途分子目录管理。`*.pt` 等权重不入库（见 `.gitignore`），
克隆仓库后需按下表补齐文件。

```
weights/
├── ppe/
│   └── ppe.pt     # PPE 检测模型（10 类，直接输出违规类 NO-*，direct 判定）
└── fire/
    └── fire.pt    # 火源/烟雾检测模型（2 类：0=smoke 1=fire，与 PPE 并行）
```

## 被哪些地方引用

| 使用方 | 路径配置 |
|---|---|
| 推理服务（本地）`inference/config.local.yaml` | `model_path: "weights/ppe/ppe.pt"`、`fire_model_path: "weights/fire/fire.pt"` |
| 推理服务（docker）`inference/config.yaml` | `weights/ppe/ppe.pt` / `weights/fire/fire.pt`（容器内挂载为 `/app/weights/...`） |
| 后端演示模式 `backend/app/config.py` | `DEMO_MODEL_PATH=/app/weights/ppe/ppe.pt`、`DEMO_FIRE_MODEL_PATH=/app/weights/fire/fire.pt`；本地由 `routers/demo.py` 自动搜索 `weights/ppe/`、`weights/fire/` |
| 原始脚本 `Safety-Detection*.py` | 默认 `weights/ppe/ppe.pt` |
| docker 挂载 `docker-compose.yml` | `./weights:/app/weights`（backend 与 inference 共用） |

## 来源

- `ppe/ppe.pt`：项目原始 PPE 模型（10 类）。
- `fire/fire.pt`：公开 HuggingFace 模型 `rabahdev/fire-smoke-yolov8n`（YOLOv8n，AGPL）。
