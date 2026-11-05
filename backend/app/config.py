"""全局配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库连接（docker-compose 中 mysql 服务名，本地开发改为 127.0.0.1）
    DATABASE_URL: str = (
        "mysql+pymysql://root:yolo123456@mysql:3306/yolo_safety?charset=utf8mb4"
    )
    # JWT 认证
    JWT_SECRET: str = "yolo-safety-secret-change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720
    # 登录账号（演示用，生产请接数据库 + 密码哈希）
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    # 抓拍图片存储目录
    UPLOAD_DIR: str = "/data/images"
    # 允许的违规类型（与 YOLO 模型类别一致）
    VIOLATION_TYPES: list = ["no_helmet", "no_vest", "no_mask"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
