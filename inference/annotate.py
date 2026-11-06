"""违规抓拍标注（与 inference/annotate.py 双份同步，修改必须同步两处）

在原始帧上绘制检测框 + 违规横幅，生成"标注证据图"：
- 违规类（NO-*）红色框
- 合规装备（Hardhat / Mask / Safety Vest）绿色框
- 其他目标（人 / 锥桶 / 机械 / 车辆）蓝色框
- 存在违规时左上角红色横幅，中文提示违规类型（优先 PIL 中文字体，无字体回退 ASCII）
"""
import os

import cv2
import numpy as np

# 与前端 views/demo/index.vue 的配色常量保持一致
NEGATIVE_CLASSES = {"NO-Hardhat", "NO-Mask", "NO-Safety Vest"}
POSITIVE_CLASSES = {"Hardhat", "Mask", "Safety Vest"}

# 违规类型 key -> 中文名称（与前端 constants/violations.ts 保持一致）
VIOLATION_LABELS = {
    "no_helmet": "未戴安全帽",
    "no_vest": "未穿安全马甲",
    "no_mask": "未戴口罩",
}

# BGR 颜色
RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)
WHITE = (255, 255, 255)
BANNER_RGB = (220, 60, 60)

# 常见中文字体路径（Windows / Linux）
_FONT_PATHS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_pil_font(size: int):
    """加载系统中文字体；找不到返回 None（调用方回退 ASCII）"""
    try:
        from PIL import ImageFont

        for path in _FONT_PATHS:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _draw_banner(img, text: str) -> np.ndarray:
    """左上角红色违规横幅；优先 PIL 渲染中文，无字体时回退 cv2 英文"""
    font_size = max(18, int(img.shape[0] * 0.035))
    try:
        from PIL import Image, ImageDraw

        font = _load_pil_font(font_size)
        if font is not None:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad = 14
            draw.rectangle(
                [pad, pad, pad + tw + 24, pad + th + 22], fill=BANNER_RGB
            )
            draw.text((pad + 12, pad + 9), text, font=font, fill=(255, 255, 255))
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        pass
    cv2.putText(
        img, f"VIOLATION: {text}", (12, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, RED, 3, cv2.LINE_AA,
    )
    return img


def draw_annotations(image, detections, violations) -> np.ndarray:
    """绘制标注证据图（不修改原图）。

    :param image: BGR 图像
    :param detections: Detection 列表（含 cls_name / conf / box）
    :param violations: 违规类型 key 列表（如 ["no_helmet"]）
    """
    img = image.copy()
    if violations:
        labels = [VIOLATION_LABELS.get(v, v) for v in violations]
        img = _draw_banner(img, "违规: " + "、".join(labels))

    for d in detections:
        x1, y1, x2, y2 = [int(v) for v in d.box]
        color = BLUE
        if d.cls_name in NEGATIVE_CLASSES:
            color = RED
        elif d.cls_name in POSITIVE_CLASSES:
            color = GREEN
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        label = f"{d.cls_name} {d.conf:.0%}" if d.conf < 1 else f"{d.cls_name} {d.conf:.2f}"
        # 标签底色 + 文字
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        ty = max(0, y1 - th - 8)
        cv2.rectangle(img, (x1, ty), (x1 + tw + 8, ty + th + 8), color, -1)
        cv2.putText(
            img, label, (x1 + 4, ty + th + 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2, cv2.LINE_AA,
        )
    return img
