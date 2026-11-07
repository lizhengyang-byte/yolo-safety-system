# 第 7 篇：YOLOv8 底层原理与 ppe.pt 模型适配——检测、判定、证据图

> 系列博客第 7 篇。系统的心脏是 AI 推理。这一篇讲透：YOLO 到底输出了什么、direct 与 person_iou 两种判定模式的底层逻辑（含 IoU 计算）、证据图怎么画，以及换模型时要改的 5 处清单。

---

## 开头：先搞清楚 YOLO 输出什么

很多人以为 YOLO"识别"出结果就完事了，但工程上**输出到判定还有一段路**。先看 YOLO 的输出形态。

YOLOv8 一次前向传播输出**若干个检测目标**，每个目标是一个 `Detection`：

```python
class Detection:
    def __init__(self, cls_id: int, cls_name: str, conf: float, box: List[float]):
        self.cls_id = cls_id     # 类别索引（ppe.pt: 0~9）
        self.cls_name = cls_name # 类别名（"NO-Hardhat" 等）
        self.conf = conf         # 置信度 0~1
        self.box = box           # 边界框 [x1, y1, x2, y2]（像素坐标）
```

一帧工地画面可能输出：

```
Detection(NO-Hardhat, conf=0.87, box=[120, 45, 310, 280])   ← 有人没戴安全帽！
Detection(Person,      conf=0.92, box=[120, 45, 310, 280])
Detection(Hardhat,     conf=0.76, box=[400, 60, 480, 130])
Detection(Safety Cone, conf=0.81, box=[50, 300, 90, 340])
```

**置信度阈值 conf**：低于阈值的框被丢弃。`conf=0.5` 表示只保留模型 50% 以上确信的检测。

## 1. detector.py：Ultralytics 的轻量封装

```python
class YoloDetector:
    def __init__(self, model_path, conf_threshold=0.5, device="cpu"):
        self.model = YOLO(model_path)          # 加载权重（首次 10~30s）
        self.names = self.model.names          # {0: "Hardhat", ...}

    def predict(self, image, conf=None) -> List[Detection]:
        conf = conf if conf is not None else self.conf_threshold
        results = self.model.predict(source=image, conf=conf, device=self.device, verbose=False)
        detections = []
        if not results: return detections
        r = results[0]
        if r.boxes is None: return detections
        for box in r.boxes:
            cls_id = int(box.cls[0]); conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(Detection(cls_id, self.names.get(cls_id, str(cls_id)), conf, [x1,y1,x2,y2]))
        return detections
```

三个细节值得记：

1. **`conf` 参数可覆盖**：演示页"灵敏度"滑块就是靠它——滑块值作为 `conf` 传给 `predict`。默认 0.5，调高 → 只认高置信度 → 框变少（更严格）；调低 → 框变多（更敏感）；
2. **`verbose=False`**：Ultralytics 默认每帧打印终端日志，视频流检测会刷屏；
3. **封装成统一 `Detection`**：屏蔽 Ultralytics 的 `Results` 对象差异——下游（judge/annotate/上报）只依赖自己的数据结构。这是**适配层模式**，换检测框架不惊动业务代码。

## 2. judge.py：违规判定，两种模式

### 2.1 direct 模式（本项目，ppe.pt）

```python
def judge_violations(detections, rule, mode="direct", iou_threshold=0.3) -> Set[str]:
    if mode == "direct":
        names = {d.cls_name for d in detections}
        return {vio for vio, cls in rule.items() if cls in names}
```

**逻辑一句话**：模型输出里出现 `NO-Hardhat` → 判 `no_helmet` 违规；出现 `NO-Mask` → `no_mask`；出现 `NO-Safety Vest` → `no_vest`。

规则表：

```python
rule = {
    "no_helmet": "NO-Hardhat",        # 违规key -> 触发违规的类别名
    "no_vest": "NO-Safety Vest",
    "no_mask": "NO-Mask",
}
```

**为什么叫 direct？** 因为"违规"是**模型直接输出的类别**，不需要任何后处理。这是 ppe.pt 这类"违规类模型"的最大优势——判定逻辑只有三行。

### 2.2 person_iou 模式（通用正类装备模型）

适用于**输出正类装备**的模型（person / helmet / vest / mask，不输出 NO-*）：

```python
persons = [d for d in detections if d.cls_name == "person"]
for person in persons:
    for vio_type, equip_cls in rule.items():      # {"no_helmet": "helmet", ...}
        equips = by_class.get(equip_cls, [])
        covered = any(_iou(person.box, e.box) >= iou_threshold for e in equips)
        if not covered:
            violations.add(vio_type)
```

**IoU 的底层原理**：IoU = Intersection over Union = 两个框的交集面积 / 并集面积。

```
        ┌──────────┐
        │ person   │     IoU = 交集面积 / 并集面积
        │   ┌──────┼──┐      = 高 → 装备"在人身上"（佩戴了）
        │   │helmet│  │
        └───┼──────┘  │    IoU 低 → 装备不在人身上（缺失）
            └─────────┘
```

判定逻辑：person 框与其附近 helmet 框的 IoU < 0.3 → 该人"未戴安全帽"。

`_iou` 实现（手写 IoU，理解它很重要）：

```python
def _iou(box_a, box_b) -> float:
    x1 = max(box_a[0], box_b[0]); y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2]); y2 = min(box_a[3], box_b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)   # 交集面积（不相交则 0）
    area_a = (box_a[2]-box_a[0]) * (box_a[3]-box_a[1])
    area_b = (box_b[2]-box_b[0]) * (box_b[3]-box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0
```

**为什么 `max(0.0, x2-x1)`？** 两个框不相交时 `x2-x1` 是负的，交集面积不能为负，所以截断为 0。

### 2.3 置信度怎么算？

`stream_worker.py` 里取"触发违规的检测框"的最大置信度：

```python
for vio in violations:
    trigger_cls = self.rule.get(vio, "")
    conf = max((d.conf for d in detections if d.cls_name == trigger_cls), default=0.0)
```

**为什么取最大？** 一帧可能有多个 NO-Hardhat 框，违规记录要存一个"置信度"字段，取最大最有代表性（模型最确信的那个）。

## 3. annotate.py：标注证据图（画给客户看的那张图）

### 3.1 配色约定（与前端一致）

```python
NEGATIVE_CLASSES = {"NO-Hardhat", "NO-Mask", "NO-Safety Vest"}   # 违规 → 红
POSITIVE_CLASSES = {"Hardhat", "Mask", "Safety Vest"}            # 合规装备 → 绿
# 其他目标（Person / Safety Cone / machinery / vehicle）→ 蓝
```

```python
def draw_annotations(image, detections, violations) -> np.ndarray:
    img = image.copy()          # 不修改原图
    if violations:
        labels = [VIOLATION_LABELS.get(v, v) for v in violations]
        img = _draw_banner(img, "违规: " + "、".join(labels))   # 左上角红色横幅
    for d in detections:
        color = BLUE
        if d.cls_name in NEGATIVE_CLASSES: color = RED
        elif d.cls_name in POSITIVE_CLASSES: color = GREEN
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)         # 检测框
        cv2.putText(img, label, ...)                             # 类别+置信度
    return img
```

### 3.2 中文横幅：为什么这么麻烦？

**底层坑**：OpenCV 的 `putText` **不支持中文**（内置字形只有 ASCII）。要在图上写"未戴安全帽"这种中文，方案是**PIL + 系统字体**：

```python
_FONT_PATHS = ["C:/Windows/Fonts/msyh.ttc", ..., "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", ...]

def _draw_banner(img, text):
    font = _load_pil_font(font_size)      # 找到系统中文就加载
    if font is not None:
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw.rectangle([...], fill=BANNER_RGB)     # 红色横幅
        draw.text((...), text, font=font, fill=(255,255,255))
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)   # 转回 BGR
    # 找不到中文字体 → 回退 ASCII 英文
    cv2.putText(img, f"VIOLATION: {text}", ...)
    return img
```

**跨平台中文字体方案**：Windows（msyh.ttc 微软雅黑）/ Linux（Noto Sans CJK）都覆盖；Docker 里都没有则回退英文。对比第 9 篇 PDF 的中文方案（reportlab 内置 STSong-Light，无需系统字体）——**每处中文渲染都有自己的坑与解法**。

### 3.3 证据图在两条链路中的应用

- 正式链路：`stream_worker.py` 的 `_report()` → `anno_image = draw_annotations(...)` → `_anno.jpg` → multipart 上传 `anno` 字段；
- 演示链路：`demo.py` → `cv2.imwrite(anno_path, anno_img)` → 入库 `anno_url` + 返回 `snapshot_url`。

## 4. 换模型清单：改了模型必须同步改 5 处

> ⚠️ 这是本仓库最重要的"改动纪律"（CLAUDE.md 明确规定）。如果你换模型（比如换成只输出正类的），必须改**全部**这些位置：

| # | 位置 | 改什么 |
|---|---|---|
| 1 | `inference/config.yaml` / `config.local.yaml` | `class_names`（与模型类别顺序一致）、`violation_rule`、`judge_mode` |
| 2 | `backend/app/config.py` | `VIOLATION_RULE`、`JUDGE_MODE`、`DEMO_MODEL_PATH`、`DEMO_CONF_THRESHOLD` |
| 3 | `backend/app/detection/annotate.py`（**同步** `inference/annotate.py`） | `NEGATIVE_CLASSES` / `POSITIVE_CLASSES` + `VIOLATION_LABELS` |
| 4 | `frontend/src/constants/violations.ts` | `VIOLATION_TYPE_MAP`、`NEGATIVE_CLASSES`、`POSITIVE_CLASSES` |
| 5 | 根目录 `Safety-Detection*.py` | 硬编码 `classNames` 列表 |

**为什么这么多处？** 因为"模型类别"渗透到：配置文件（推理）、配置文件（后端）、标注配色（后端双份）、前端画框配色、原始脚本——**一处模型改动，五处代码响应**。这是"模型与代码强耦合"的代价，也是文档必须记录这份清单的原因。

验证类别顺序的方法：`YOLO(path).names` 打印模型实际类别字典，与 `class_names` 配置比对。

## 5. 推理链路全景回顾

```
摄像头帧（BGR ndarray）
  → detector.predict()       # YOLO 检测 → List[Detection]
  → judge_violations()       # 判定 → Set[violation keys]
  → draw_annotations()       # 画证据图（仅违规帧）
  → _report()                # 去重 → 存双图 → multipart 上报
  → violations 入库          # 后端
  → trigger_warning_check()  # 预警检查（第 9 篇）
```

**三个文件各司其职、互不越界**：detector 只负责"看到了什么"，judge 只负责"算不算违规"，annotate 只负责"怎么画"。单一职责是它们能被复用的前提（双份同步也靠这个）。

## 总结

- **YOLO 输出**：类别 + 置信度 + 边界框；conf 阈值过滤；
- **detector.py**：Ultralytics 轻量封装（适配层），conf 参数支持覆盖；
- **judge.py**：direct（出现违规类即违规，ppe.pt 用）+ person_iou（person 与装备框 IoU 判定，手写 IoU）；
- **annotate.py**：红/绿/蓝配色 + PIL 中文横幅（跨平台字体兜底）；
- **换模型 = 改 5 处**（配置文件×2 + 双份 annotate + 前端常量 + 原始脚本）；
- **核心纪律**：detector/judge/annotate 双份同步。

**下一篇：[第 8 篇：Vue3 后台是怎么写出来的——路由、布局、canvas 叠加、8 个页面](08-前端实战-Vue3后台管理系统.md)**
