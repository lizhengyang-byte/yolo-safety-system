# 第 6 篇：后端从零拆解——FastAPI 启动流程、四张表、JWT 认证

> 系列博客第 6 篇。后端代码逐个文件拆开讲。不只看"写了什么"，更讲"为什么这么写"。从应用启动、配置管理、数据模型、JWT 认证到路由实战，一次讲透。

---

## 开头：后端 = 接口 + 数据 + 认证 + 业务

一个后台系统的后端，无非四件事：**提供接口、管理数据、保证安全、实现业务**。FastAPI 把这四件事都包圆了。这篇我们逐个看。

后端文件地图：

```
backend/
├── app/
│   ├── main.py              # 应用入口：建表、schema 演进、CORS、静态目录、模型预热、路由注册
│   ├── config.py            # Settings：数据库/JWT/违规规则/模型/阈值
│   ├── database.py          # 引擎 + 会话（SQLite/MySQL 双兼容）
│   ├── models.py            # 四张 ORM 表 + 本地时间戳约定
│   ├── security.py          # JWT 创建/解码/依赖
│   ├── detection/           # detector/judge/annotate（与 inference 双份同步）
│   ├── services/warnings.py # 预警触发服务
│   └── routers/             # auth/cameras/violations/logs/demo/warnings
├── pyproject.toml           # uv 工程配置
├── init.sql                 # 生产建库建表（可选）
└── Dockerfile
```

## 1. 应用启动：main.py 逐段拆解

### 1.1 建表：零依赖开箱即用的关键

```python
Base.metadata.create_all(bind=engine)
```

**底层原理**：SQLAlchemy 扫描 `models.py` 中所有继承 `Base` 的类（Camera、Violation、WarningRule、WarningEvent），自动生成 `CREATE TABLE` 语句执行。**第一次启动自动建好 4 张表**——这就是"本地零依赖可跑"的根基：不需要任何数据库管理员操作。

### 1.2 Schema 演进：`create_all` 的坑

```python
def _ensure_schema():
    """轻量 schema 演进：为已存在的 violations 表补齐新增列（SQLite/MySQL 通用）"""
    inspector = inspect(engine)
    existing = {c["name"] for c in inspector.get_columns("violations")}
    for col, ddl in {"anno_url": "VARCHAR(512)", "detections_json": "TEXT"}.items():
        if col not in existing:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE violations ADD COLUMN {col} {ddl}"))
```

**底层原因**：`create_all` 只建"不存在的表"，**不会修改已存在的表**。产品上线后要加字段（这里是加 `anno_url` 标注证据图、`detections_json` 检测明细），要么用迁移工具（alembic），要么像这样写个**幂等的补列函数**——启动时自动检查、缺啥补啥，旧库无缝升级。幂等的含义：每次启动都执行，但只在"列不存在"时才 ALTER，所以不会出错。

### 1.3 静态目录 + CORS + 路由注册

```python
app.mount("/images", StaticFiles(directory=settings.UPLOAD_DIR), name="images")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["摄像头"])
app.include_router(violations.router, prefix="/api/violations", tags=["违规记录"])
app.include_router(logs.router, prefix="/api/logs", tags=["安全日志"])
app.include_router(demo.router, prefix="/api/demo", tags=["临时演示"])
app.include_router(warnings.router, prefix="/api/warnings", tags=["预警中心"])
```

三个要点：
- `/images` 静态挂载：抓拍图片直接通过 URL 访问（`image_url = "/images/xxx.jpg"`）；
- CORS 放开：前端在其他端口/域名访问后端时不会被浏览器拦截；
- 六个路由模块按业务域划分，每个有统一 `prefix`。

### 1.4 模型预热：演示体验的关键

```python
def _warmup_demo_model():
    """后台线程预热演示模型：避免首次 /api/demo/detect 加载模型卡顿 10~30s"""
    from .routers import demo
    demo.get_detector()          # 触发懒加载单例

@app.on_event("startup")
def startup_warmup():
    threading.Thread(target=_warmup_demo_model, daemon=True).start()
```

**底层原理**：YOLO 加载 100MB 级权重需要 10~30 秒。如果等客户点"开始演示"才加载，体验就是"卡死"。预热线程让模型在**后端启动时**就绪——这是"产品思维"在代码里的落点（第 3 篇的 P0-3）。

## 2. 配置管理：config.py 的一切皆可覆盖

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./yolo_safety.db"   # 本地默认 SQLite
    JWT_SECRET: str = "yolo-safety-secret-change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720                      # 12 小时
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    UPLOAD_DIR: str = "./images"
    VIOLATION_TYPES: list = ["no_helmet", "no_vest", "no_mask"]
    VIOLATION_RULE: dict = {
        "no_helmet": "NO-Hardhat",
        "no_vest": "NO-Safety Vest",
        "no_mask": "NO-Mask",
    }
    JUDGE_MODE: str = "direct"
    DEMO_MODEL_PATH: str = "/app/weights/ppe/ppe.pt"   # Docker 挂载路径
    DEMO_CONF_THRESHOLD: float = 0.5
    DEMO_DEVICE: str = "cpu"
```

**底层原理**：pydantic-settings 的优先级是 **代码默认值 < .env 文件 < 环境变量**。Docker 里设置 `DATABASE_URL=mysql+pymysql://...` 环境变量就直接覆盖默认值——同一份代码，本地跑 SQLite，Docker 跑 MySQL，无需改代码。

业务规则（违规规则、判定模式）也集中在这里：换模型只改一处（后端侧）。

> ⚠️ 注意：`ADMIN_USERNAME/PASSWORD` 是演示用硬编码（注释明确写了"生产请接数据库 + 密码哈希"）。JWT_SECRET 也标注了"change-me-in-prod"。

## 3. 数据模型：models.py 四张表

### 3.1 时间戳陷阱（全项目最痛的坑）

```python
# 时间戳统一用 Python 本地时间写入（不用 server_default 的 CURRENT_TIMESTAMP：
# SQLite 的 CURRENT_TIMESTAMP 是 UTC，与业务层的本地时间比较会差 8 小时）
_ts = datetime.now
```

**底层原理**：SQLAlchemy 的 `server_default=_func.now()` 在 SQLite 上生成 `CURRENT_TIMESTAMP`，而 **SQLite 的 CURRENT_TIMESTAMP 返回 UTC 时间**（格林尼治），业务层用 `datetime.now()`（本地时间，UTC+8）比较 → 所有时间窗口统计（预警、今日统计、趋势）**永远差 8 小时**。

修复：所有时间戳列用 Python 侧 `default=datetime.now` 写入（本地时间），存量 SQLite 数据做一次性 `+8 hours` 迁移。MySQL 的 `NOW()` 本身就是服务器本地时间，无此问题。

> ⚠️ CLAUDE.md 警告：**不要改回 `server_default=_func.now()`**——踩过坑后立的规矩。第 9 篇完整展开。

### 3.2 四张表逐个看

**① cameras 摄像头表**

```python
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)        # 摄像头名称
    location = Column(String(128), default="")       # 安装点位（看板点位排行用）
    rtsp_url = Column(String(512), nullable=False)   # RTSP 地址
    status = Column(String(16), default="offline")   # online/offline（心跳更新）
    enabled = Column(Boolean, default=True)          # 推理服务只拉启用中的
    created_at = Column(DateTime, default=_ts)
```

**② violations 违规记录表**

```python
class Violation(Base):
    __tablename__ = "violations"
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, index=True)          # 演示链路为 0
    camera_name = Column(String(64), default="")
    violation_type = Column(String(32), index=True)  # no_helmet / no_vest / no_mask
    confidence = Column(Float, default=0.0)          # 置信度
    image_path = Column(String(512))                 # 本地路径
    image_url = Column(String(512))                  # 访问地址 /images/xxx.jpg
    anno_url = Column(String(512), default="")       # 标注证据图地址（P0-1 新增）
    detections_json = Column(Text, default="")       # 帧内检测明细 JSON（P0-1 新增）
    created_at = Column(DateTime, default=_ts, index=True)

    @property
    def detections(self) -> list | None:
        """解析 detections_json；为空或非法时返回 None"""
```

**设计要点**：
- `violation_type` 存 key（`no_helmet`）不存中文——**存 key、不存显示名**是数据设计准则（第 1 篇讲过）；
- `detections_json` 存 JSON 文本：该帧全部检测目标（类别/置信度/坐标），详情页"帧内检测明细"用；
- `@property detections`：把 JSON 解析封装成属性，前端拿到的直接是 list。

**③④ warning_rules / warning_events 预警表（阶段四新增）**

```python
class WarningRule(Base):
    __tablename__ = "warning_rules"
    id, name
    camera_id = Column(Integer, nullable=True)       # 空=全部摄像头
    violation_type = Column(String(32), nullable=True)  # 空=全部类型
    threshold = Column(Integer, default=3)           # 窗口内违规次数阈值
    window_minutes = Column(Integer, default=60)     # 统计窗口（分钟）
    enabled = Column(Boolean, default=True)

class WarningEvent(Base):
    __tablename__ = "warning_events"
    id, rule_id                                      # 触发的规则
    camera_id, camera_name, violation_type
    count = Column(Integer, default=0)               # 窗口内违规次数
    triggered_at = Column(DateTime, default=_ts, index=True)
    is_read = Column(Boolean, default=False)         # 铃铛未读数
```

**设计精妙处**：规则表用"**空值 = 通配**"表示"全部摄像头/全部类型"——用 `nullable` 而不是枚举"all"。这大大简化了规则匹配逻辑（第 9 篇详述）。

## 4. JWT 认证：无状态登录的底层原理

### 4.1 JWT 是什么？

JWT（JSON Web Token）是**无状态**认证方案：服务器签发一个带签名的令牌，客户端每次请求带上，服务器验签即可——**不需要在服务器存会话**（对比 session 方案）。

### 4.2 三段式结构

一个 JWT 长这样：`xxxxx.yyyyy.zzzzz`（用 `.` 分成三段）：

1. **Header**：算法信息（`{"alg": "HS256", "typ": "JWT"}`）；
2. **Payload**：载荷（用户名、过期时间等业务数据）；
3. **Signature**：签名 = `HMAC(header.payload, SECRET)`——**防篡改的关键**。

签名保证：Payload 里的内容**一旦被改动，签名对不上**，服务器直接拒绝。所以"用户名"只能被服务器签发。

### 4.3 本项目的实现（security.py）

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_minutes=None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI 依赖：从请求头提取 Bearer token → 解码 → 校验"""
    payload = decode_token(token)
    username = payload.get("sub")
    if username is None:
        raise credentials_exception
    return {"username": username}
```

**FastAPI 依赖注入的妙处**：`get_current_user` 作为一个 `Depends`，可以挂在任何需要认证的接口上。FastAPI 自动从请求头提取 `Authorization: Bearer xxx`，解码校验，校验失败返回 401。**业务代码一行认证逻辑都不用写**。

### 4.4 前端配合（request.ts）

```typescript
request.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;   // 自动附加
  return config;
});
request.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    if (status === 401) { localStorage.removeItem("token"); window.location.href = "/login"; }
    ...
  });
```

前端只做两件事：**请求时带 token、收到 401 跳登录**。所有业务接口的权限由后端 `Depends(get_current_user)` 统一保证。

## 5. 路由实战：auth / cameras / violations

### 5.1 auth.py（登录）

```python
@router.post("/login")
def login(data: LoginRequest):
    if data.username != settings.ADMIN_USERNAME or data.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": data.username})
    return {"access_token": token, "token_type": "bearer"}
```

### 5.2 cameras.py（CRUD + 测试连接）

```python
@router.get("")
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).order_by(Camera.id).all()          # 推理服务也调它

@router.post("")
def create_camera(body: CameraCreate, db: Session = Depends(get_db)):
    cam = Camera(**body.model_dump())
    db.add(cam); db.commit(); db.refresh(cam)
    return cam

@router.post("/test")
def test_camera(body: CameraTest, db: Session = Depends(get_db)):
    """RTSP 连通性测试（8 秒兜底，不可阻塞事件循环）"""
```

`/test` 的实现要点（P1-3，产品需求"录了连不上的摄像头不能忍"）：
- 用 `ThreadPoolExecutor` 提交 OpenCV 试拉任务，`shutdown(wait=False)` 防止挂死；
- 超时 8 秒返回"连接超时"；区分认证失败/地址格式错误；
- 返回结构化错误，前端显示明确原因。

### 5.3 violations.py（违规入库：正式链路的终点）

两个上报入口：

```python
@router.post("/report")              # 兼容老版（JSON body）
def report_violation(body: ViolationCreate, db):
    v = Violation(**body.model_dump())
    db.add(v); db.commit()
    trigger_warning_check(db, v.camera_id, v.camera_name, v.violation_type)
    return {"id": v.id}

@router.post("/with-image")          # 新版（multipart，推理服务用）
async def report_violation_with_image(
    file: UploadFile = File(...),
    anno: UploadFile = File(...),          # 标注证据图（P0-1 新增）
    camera_id: int = Form(...),
    camera_name: str = Form(""),
    violation_type: str = Form(...),
    confidence: float = Form(0.0),
    detections: str = Form(""),            # 帧内检测明细 JSON
    db: Session = Depends(get_db),
):
    # 保存图片到 UPLOAD_DIR
    # 构造 Violation（image_url=/images/fname, anno_url=/images/anno_fname）
    db.add(v); db.commit()
    trigger_warning_check(db, camera_id, camera_name, violation_type)
    return {"id": v.id, "url": f"/images/{fname}", ...}
```

**multipart 细节**：FastAPI 用 `UploadFile = File(...)` 收图片、`Form(...)` 收表单字段。文件命名规则 `cam{camera_id}_{violation_type}_{timestamp}.jpg`——从文件名就能看出"哪个摄像头、什么违规、什么时候"。

**预警触发链**：两条入库路径 commit 后都调 `trigger_warning_check`（第 9 篇详述）——匹配启用规则 → 统计窗口违规数 ≥ 阈值 → 生成 `warning_events`。

## 6. SQLAlchemy 查询速成（后面几篇反复用）

| 场景 | 写法 |
|---|---|
| 全表查询 | `db.query(Camera).order_by(Camera.id).all()` |
| 条件过滤 | `db.query(Violation).filter(Violation.camera_id == 1)` |
| 聚合计数 | `db.query(func.count(Violation.id)).scalar()` |
| 分组统计 | `db.query(Violation.violation_type, func.count(Violation.id)).group_by(...).all()` |
| 日期过滤 | `db.query(...).filter(Violation.created_at >= "2026-11-01 00:00:00")` |
| 联表 | `db.query(...).outerjoin(Camera, Violation.camera_id == Camera.id)` |

## 总结

- **启动流程**：建表 → schema 演进（幂等补列）→ 静态目录 → CORS → 预热模型 → 注册路由；
- **配置**：pydantic-settings，代码默认值 < .env < 环境变量（本地 SQLite / Docker MySQL 一套代码）；
- **数据设计**：存 key 不存显示名、JSON 明细列、空值=通配（预警规则）、本地时间戳（防 UTC 陷阱）；
- **JWT**：三段式无状态令牌，签名防篡改，FastAPI 依赖注入统一认证；
- **路由**：每个业务域一个 router，`Depends(get_db)` 管理会话，commit 后触发预警检查。

**下一篇：[第 7 篇：YOLOv8 底层原理与 ppe.pt 模型适配——检测、判定、证据图](07-推理实战-YOLOv8检测判定与抓拍.md)**
