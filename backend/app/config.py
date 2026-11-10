"""全局配置

已适配当前项目（ppe.pt 模型）：
- VIOLATION_RULE 使用 ppe.pt 直接输出的违规类（NO-Hardhat / NO-Mask / NO-Safety Vest）
- JUDGE_MODE=direct（出现违规类即判定，无需 IoU）
- 默认 DATABASE_URL 为 SQLite，本地无需 MySQL 即可运行；
  docker-compose 中通过环境变量覆盖为 MySQL
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库连接（本地默认 SQLite，零依赖开箱即用；
    # docker-compose 中覆盖为 mysql+pymysql://...）
    DATABASE_URL: str = "sqlite:///./yolo_safety.db"
    # JWT 认证
    JWT_SECRET: str = "yolo-safety-secret-change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720
    # 登录账号（演示用，生产请接数据库 + 密码哈希）
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    # 抓拍图片存储目录（本地默认 backend/images/，docker-compose 覆盖为 /data/images）
    UPLOAD_DIR: str = "./images"
    # 允许的违规类型（系统级 key，前端展示中文）
    VIOLATION_TYPES: list = [
        "no_helmet",
        "no_vest",
        "no_mask",
        "fire",
        "smoke",
        "zone_intrusion",
    ]
    # 违规判定规则：违规类型 -> 触发违规的类别名（与 ppe.pt 类别一致）
    # 火源/烟雾由独立 fire.pt 模型检测（见下方 FIRE_* 配置），同样走 direct 判定
    VIOLATION_RULE: dict = {
        "no_helmet": "NO-Hardhat",
        "no_vest": "NO-Safety Vest",
        "no_mask": "NO-Mask",
    }
    # 违规判定模式：direct（ppe.pt 直接输出违规类）/ person_iou（正类装备模型）
    JUDGE_MODE: str = "direct"
    # 临时演示模式：后端直接加载模型推理（不依赖 RTSP/推理服务）
    # docker 中挂载路径为 /app/weights/ppe.pt；本地开发可设 .env 覆盖，
    # 或由 demo.py 自动搜索相对路径（见 routers/demo.py）
    DEMO_MODEL_PATH: str = "/app/weights/ppe.pt"
    DEMO_CONF_THRESHOLD: float = 0.5
    DEMO_DEVICE: str = "cpu"

    # ---------- 火源火灾检测（第二模型，与 PPE 并行；演示模式与正式链路一致）----------
    DEMO_FIRE_ENABLED: bool = True
    # 火源/烟雾模型权重（YOLOv8n，2 类：0=smoke 1=fire），docker 挂载 /app/weights/fire.pt
    DEMO_FIRE_MODEL_PATH: str = "/app/weights/fire.pt"
    DEMO_FIRE_CONF_THRESHOLD: float = 0.4
    # 火源违规判定规则：出现 fire / smoke 即违规（direct）
    FIRE_VIOLATION_RULE: dict = {
        "fire": "fire",
        "smoke": "smoke",
    }

    # ---------- 预警邮件通知（SMTP）----------
    # 未配置 SMTP_HOST / MAIL_TO 时自动跳过发送，不影响系统运行
    MAIL_ENABLED: bool = True
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SSL: bool = True          # 465 端口一般用 SSL
    SMTP_STARTTLS: bool = False    # 587 端口一般用 STARTTLS（此时 SMTP_SSL=False）
    MAIL_FROM: str = ""            # 发件人，留空则用 SMTP_USER
    MAIL_TO: str = ""              # 收件人，多个用英文逗号分隔

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
