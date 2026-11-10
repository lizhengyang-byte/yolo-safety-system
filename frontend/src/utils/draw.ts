/** 检测框叠加绘制（演示页 / 实时监控页共用） */
import { NEGATIVE_CLASSES, POSITIVE_CLASSES, FIRE_CLASSES, VIOLATION_TYPE_MAP } from "@/constants/violations";

export interface DrawableDetection {
  cls_name: string;
  conf: number;
  box: [number, number, number, number];
}

/** 危险区域多边形（归一化顶点 [[x,y],...] 0~1） */
export interface DrawableZone {
  zone_name: string;
  polygon: number[][];
}

/**
 * 在画布上绘制危险区域多边形（归一化坐标 -> 像素映射）。
 * 应在 drawDetections 之前调用（区域在下层，检测框在上层）。
 * @param hit 是否命中（命中时紫红填充高亮）
 */
export function drawZones(
  canvas: HTMLCanvasElement,
  zones: DrawableZone[],
  hit = false
) {
  const ctx = canvas.getContext("2d");
  if (!ctx || !zones.length) return;
  const W = canvas.width;
  const H = canvas.height;
  for (const z of zones) {
    const poly = z.polygon;
    if (!poly || poly.length < 3) continue;
    ctx.beginPath();
    ctx.moveTo(poly[0][0] * W, poly[0][1] * H);
    for (let i = 1; i < poly.length; i++) ctx.lineTo(poly[i][0] * W, poly[i][1] * H);
    ctx.closePath();
    ctx.fillStyle = "rgba(217, 70, 239, 0.16)"; // 紫红半透明填充
    ctx.fill();
    ctx.strokeStyle = "#d946ef";
    ctx.lineWidth = hit ? 3 : 2;
    ctx.setLineDash(hit ? [] : [6, 4]);
    ctx.stroke();
    ctx.setLineDash([]);
    if (z.zone_name) {
      ctx.fillStyle = "rgba(0,0,0,0.6)";
      const tw = ctx.measureText(z.zone_name).width + 10;
      ctx.fillRect(poly[0][0] * W, poly[0][1] * H - 20, tw, 18);
      ctx.fillStyle = "#e879f9";
      ctx.font = "bold 13px sans-serif";
      ctx.fillText(z.zone_name, poly[0][0] * W + 5, poly[0][1] * H - 6);
    }
  }
}

/**
 * 在画布上绘制检测框 + 违规横幅。
 * @param onlyViolations true 时只画违规目标（"只看违规"模式）
 */
export function drawDetections(
  canvas: HTMLCanvasElement,
  detections: DrawableDetection[],
  violations: string[],
  onlyViolations = false,
  zones?: DrawableZone[]
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 先画危险区域多边形（在下层），再画检测框
  if (zones && zones.length) {
    drawZones(canvas, zones, false);
  }

  for (const d of detections) {
    if (onlyViolations && !NEGATIVE_CLASSES.has(d.cls_name) && !FIRE_CLASSES.has(d.cls_name)) continue;
    const [x1, y1, x2, y2] = d.box;
    const w = x2 - x1;
    const h = y2 - y1;

    let color = "#409eff"; // 蓝：其他目标
    if (POSITIVE_CLASSES.has(d.cls_name)) color = "#67c23a"; // 绿：合规装备
    if (NEGATIVE_CLASSES.has(d.cls_name)) color = "#f56c6c"; // 红：违规
    if (FIRE_CLASSES.has(d.cls_name)) color = "#ff7d00"; // 橙：火源/烟雾

    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x1, y1, w, h);

    const label = `${d.cls_name} ${(d.conf * 100).toFixed(0)}%`;
    ctx.fillStyle = color;
    ctx.font = "bold 16px sans-serif";
    const tw = ctx.measureText(label).width + 10;
    ctx.fillRect(x1, y1 - 22, tw, 22);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x1 + 5, y1 - 5);
  }

  // 违规横幅（顶部）
  if (violations.length) {
    const text = "⚠ 违规: " + violations.map((v) => VIOLATION_TYPE_MAP[v] || v).join("、");
    ctx.font = "bold 18px sans-serif";
    const tw = ctx.measureText(text).width + 24;
    ctx.fillStyle = "#f56c6c";
    ctx.fillRect(12, 12, tw, 34);
    ctx.fillStyle = "#fff";
    ctx.fillText(text, 24, 36);
  }
}
