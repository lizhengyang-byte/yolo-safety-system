"""数据库连接与会话"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

# SQLite（本地开发）与 MySQL（docker）的引擎参数不同：
# SQLite 无需连接池参数，且 FastAPI 多线程访问需 check_same_thread=False
engine_kwargs = (
    {"connect_args": {"check_same_thread": False}, "echo": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
        "echo": False,
    }
)
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
