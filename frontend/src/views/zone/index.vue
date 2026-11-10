<template>
  <el-card>
    <template #header>
      <div class="card-head-row">
        <div class="card-head-title">
          <span class="ico"><el-icon><Aim /></el-icon></span>
          危险区域配置（多边形 ROI）
        </div>
        <el-tooltip
          content="为每个摄像头单独配置危险多边形区域。人员落脚点进入区域且满足置信度/停留时长即判为“危险区域闯入”。"
          placement="top"
        >
          <el-icon class="hint-ico"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
    </template>

    <el-alert
      type="info"
      :closable="false"
      style="margin-bottom: 14px"
      title="操作：1) 选择摄像头 → 2) 载入该摄像头画面截图（上传快照）→ 3) 在画面上依次点击顶点绘制多边形 → 4) 填写区域名称等参数 → 5) 保存。坐标为归一化值，分辨率变化不影响。"
    />

    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <el-select
        v-model="cameraId"
        placeholder="选择摄像头"
        style="width: 220px"
        @change="onCameraChange"
      >
        <el-option v-for="c in cameras" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>

      <input ref="fileRef" type="file" accept="image/*" style="display: none" @change="onFilePicked" />
      <el-button :disabled="!cameraId" @click="fileRef?.click()">
        <el-icon class="btn-ico"><Upload /></el-icon>上传画面快照
      </el-button>
      <el-button :disabled="!cameraId" @click="loadLatestCapture">
        <el-icon class="btn-ico"><Refresh /></el-icon>载入最近一张抓拍
      </el-button>

      <el-divider direction="vertical" />
      <el-button :disabled="points.length < 3" type="primary" @click="finishPolygon">
        <el-icon class="btn-ico"><Check /></el-icon>完成当前多边形（{{ points.length }} 点）
      </el-button>
      <el-button :disabled="points.length === 0" @click="clearCurrent">
        <el-icon class="btn-ico"><Delete /></el-icon>清空当前
      </el-button>
    </div>

    <div class="editor-wrap">
      <!-- 画布区 -->
      <div class="canvas-box" ref="canvasBoxRef">
        <div v-if="!baseImage" class="canvas-empty">
          <el-icon :size="48"><Picture /></el-icon>
          <p>请先选择摄像头并上传/载入画面快照</p>
        </div>
        <div v-else class="canvas-inner">
          <img ref="imgRef" :src="baseImage" class="base-img" @load="onImgLoad" />
          <canvas
            ref="canvasRef"
            class="overlay-canvas"
            @click="onCanvasClick"
            @mousemove="onCanvasMove"
          ></canvas>
        </div>
      </div>

      <!-- 右侧：当前多边形表单 + 已保存列表 -->
      <div class="side-panel">
        <el-card shadow="never" class="form-card">
          <template #header><b>当前多边形</b></template>
          <el-form label-width="96px" size="small">
            <el-form-item label="区域名称">
              <el-input v-model="form.zone_name" placeholder="如：深基坑西侧" />
            </el-form-item>
            <el-form-item label="区域类别">
              <el-select v-model="form.zone_type" style="width: 100%">
                <el-option
                  v-for="(label, val) in ZONE_TYPE_LABELS"
                  :key="val"
                  :label="label"
                  :value="val"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="置信度阈值">
              <el-input-number v-model="form.min_confidence" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </el-form-item>
            <el-form-item label="停留(秒)">
              <el-input-number v-model="form.min_dwell_seconds" :min="0" :max="60" :step="0.5" style="width: 100%" />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="form.enabled" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="points.length < 3 || !form.zone_name" @click="saveZone">
                保存该区域
              </el-button>
            </el-form-item>
          </el-form>
          <div class="hint-text">提示：点击画面添加顶点，至少 3 个点（自动闭合）。</div>
        </el-card>

        <el-card shadow="never" class="list-card">
          <template #header><b>该摄像头已配置区域（{{ zones.length }}）</b></template>
          <el-empty v-if="!zones.length" description="暂无区域" :image-size="60" />
          <div v-for="z in zones" :key="z.id" class="zone-item">
            <div class="zone-info">
              <div class="zone-title">
                <el-tag size="small" effect="dark" type="danger">{{ z.zone_name }}</el-tag>
                <span class="zone-type">{{ ZONE_TYPE_LABELS[z.zone_type] || z.zone_type }}</span>
              </div>
              <div class="zone-meta">
                置信度 ≥{{ z.min_confidence }} · 停留 ≥{{ z.min_dwell_seconds }}s · {{ z.polygon.length }} 点
                <el-tag v-if="!z.enabled" size="small" type="info">停用</el-tag>
              </div>
            </div>
            <div class="zone-actions">
              <el-switch v-model="z.enabled" size="small" @change="(v:boolean)=>toggleZone(z, v)" />
              <el-button size="small" text type="danger" @click="removeZone(z)">删除</el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onBeforeUnmount, reactive, ref, nextTick } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { listCameras, type Camera } from "@/api/camera";
import {
  listZones,
  createZone,
  updateZone,
  deleteZone,
  ZONE_TYPE_LABELS,
  type DangerZone,
  type DangerZoneInput,
} from "@/api/zone";
import { listViolations } from "@/api/violation";

const cameras = ref<Camera[]>([]);
const cameraId = ref<number | null>(null);
const zones = ref<DangerZone[]>([]);

const fileRef = ref<HTMLInputElement | null>(null);
const imgRef = ref<HTMLImageElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const canvasBoxRef = ref<HTMLDivElement | null>(null);

const baseImage = ref<string>("");
const points = ref<number[][]>([]); // 归一化顶点
const cursor = ref<{ x: number; y: number } | null>(null); // 归一化光标
let imgNaturalW = 0;
let imgNaturalH = 0;

const form = reactive({
  zone_name: "",
  zone_type: "danger",
  min_confidence: 0.4,
  min_dwell_seconds: 2.0,
  enabled: true,
});

// ---------- 摄像头 ----------
async function loadCameras() {
  try {
    cameras.value = await listCameras();
  } catch {
    /* 静默 */
  }
}

async function onCameraChange() {
  points.value = [];
  cursor.value = null;
  if (cameraId.value == null) {
    zones.value = [];
    return;
  }
  await loadZones();
}

async function loadZones() {
  if (cameraId.value == null) return;
  try {
    zones.value = await listZones(cameraId.value);
    redraw();
  } catch {
    zones.value = [];
  }
}

// ---------- 载入底图 ----------
function onFilePicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const f = input.files?.[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    baseImage.value = String(reader.result || "");
    points.value = [];
    nextTick(() => {
      if (imgRef.value?.complete) onImgLoad();
    });
  };
  reader.readAsDataURL(f);
  input.value = "";
}

async function loadLatestCapture() {
  if (cameraId.value == null) return;
  try {
    const res = await listViolations({ camera_id: cameraId.value, page: 1, page_size: 1 });
    const items = (res as any).items || (res as any) || [];
    const latest = items[0];
    const url = latest?.anno_url || latest?.image_url;
    if (!url) {
      ElMessage.warning("该摄像头暂无抓拍图片，请上传画面快照");
      return;
    }
    baseImage.value = url;
    points.value = [];
    nextTick(() => {
      if (imgRef.value?.complete) onImgLoad();
    });
  } catch {
    ElMessage.error("载入抓拍失败");
  }
}

// ---------- 画布绘制 ----------
function onImgLoad() {
  const img = imgRef.value;
  if (!img) return;
  imgNaturalW = img.naturalWidth;
  imgNaturalH = img.naturalHeight;
  resizeCanvas();
  redraw();
}

function resizeCanvas() {
  const img = imgRef.value;
  const canvas = canvasRef.value;
  if (!img || !canvas) return;
  canvas.width = img.clientWidth;
  canvas.height = img.clientHeight;
}

function redraw() {
  const canvas = canvasRef.value;
  const ctx = canvas?.getContext("2d");
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const W = canvas.width;
  const H = canvas.height;

  // 已保存区域（半透明紫红填充 + 描边 + 名称）
  for (const z of zones.value) {
    drawPoly(ctx, z.polygon, W, H, z.enabled ? "#d946ef" : "#9ca3af", true, z.zone_name);
  }
  // 当前正在绘制的多边形
  if (points.value.length) {
    drawPoly(ctx, points.value, W, H, "#ff4d4f", false);
    // 顶点 + 光标预览线
    ctx.fillStyle = "#ff4d4f";
    for (const p of points.value) {
      ctx.beginPath();
      ctx.arc(p[0] * W, p[1] * H, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    if (cursor.value) {
      const last = points.value[points.value.length - 1];
      ctx.strokeStyle = "rgba(255,77,79,0.6)";
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(last[0] * W, last[1] * H);
      ctx.lineTo(cursor.value.x * W, cursor.value.y * H);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
}

function drawPoly(
  ctx: CanvasRenderingContext2D,
  poly: number[][],
  W: number,
  H: number,
  color: string,
  fill: boolean,
  label?: string
) {
  if (poly.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(poly[0][0] * W, poly[0][1] * H);
  for (let i = 1; i < poly.length; i++) {
    ctx.lineTo(poly[i][0] * W, poly[i][1] * H);
  }
  if (fill && poly.length >= 3) {
    ctx.closePath();
    ctx.fillStyle = color + "33";
    ctx.fill();
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
  if (label) {
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    const tw = ctx.measureText(label).width + 10;
    ctx.fillRect(poly[0][0] * W, poly[0][1] * H - 22, tw, 18);
    ctx.fillStyle = "#fff";
    ctx.font = "13px sans-serif";
    ctx.fillText(label, poly[0][0] * W + 5, poly[0][1] * H - 8);
  }
}

function getNormalized(e: MouseEvent): { x: number; y: number } | null {
  const canvas = canvasRef.value;
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) / rect.width;
  const y = (e.clientY - rect.top) / rect.height;
  if (x < 0 || x > 1 || y < 0 || y > 1) return null;
  return { x: Math.round(x * 10000) / 10000, y: Math.round(y * 10000) / 10000 };
}

function onCanvasClick(e: MouseEvent) {
  const p = getNormalized(e);
  if (!p) return;
  points.value.push([p.x, p.y]);
  redraw();
}

function onCanvasMove(e: MouseEvent) {
  if (!points.value.length) return;
  const p = getNormalized(e);
  cursor.value = p;
  redraw();
}

// ---------- 保存 / 管理 ----------
async function saveZone() {
  if (cameraId.value == null) return;
  if (points.value.length < 3) {
    ElMessage.warning("至少需要 3 个顶点");
    return;
  }
  if (!form.zone_name.trim()) {
    ElMessage.warning("请填写区域名称");
    return;
  }
  const payload: DangerZoneInput = {
    camera_id: cameraId.value,
    zone_name: form.zone_name.trim(),
    zone_type: form.zone_type,
    polygon: points.value,
    min_confidence: form.min_confidence,
    min_dwell_seconds: form.min_dwell_seconds,
    enabled: form.enabled,
  };
  try {
    await createZone(payload);
    ElMessage.success("区域已保存");
    points.value = [];
    cursor.value = null;
    form.zone_name = "";
    await loadZones();
  } catch {
    /* 拦截器已提示 */
  }
}

function finishPolygon() {
  if (points.value.length < 3) {
    ElMessage.warning("至少需要 3 个顶点");
    return;
  }
  ElMessage.info("多边形已绘制，请在右侧填写名称并保存");
}

function clearCurrent() {
  points.value = [];
  cursor.value = null;
  redraw();
}

async function toggleZone(z: DangerZone, val: boolean) {
  try {
    await updateZone(z.id, { enabled: val });
  } catch {
    z.enabled = !val;
  }
}

async function removeZone(z: DangerZone) {
  try {
    await ElMessageBox.confirm(`确定删除区域「${z.zone_name}」？`, "提示", { type: "warning" });
  } catch {
    return;
  }
  try {
    await deleteZone(z.id);
    ElMessage.success("已删除");
    await loadZones();
  } catch {
    /* 拦截器已提示 */
  }
}

// 窗口尺寸变化时重绘
function onResize() {
  resizeCanvas();
  redraw();
}
window.addEventListener("resize", onResize);
onBeforeUnmount(() => window.removeEventListener("resize", onResize));

loadCameras();
</script>

<style scoped>
.card-head-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-head-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.hint-ico {
  color: #909399;
  cursor: help;
}
.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}
.editor-wrap {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.canvas-box {
  flex: 1;
  min-width: 320px;
  background: #1e1e1e;
  border-radius: 8px;
  min-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.canvas-empty {
  color: #888;
  text-align: center;
}
.canvas-inner {
  position: relative;
  width: 100%;
  line-height: 0;
}
.base-img {
  width: 100%;
  height: auto;
  display: block;
  user-select: none;
}
.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  cursor: crosshair;
}
.side-panel {
  width: 340px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.hint-text {
  font-size: 12px;
  color: #909399;
}
.zone-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed #eee;
}
.zone-item:last-child {
  border-bottom: none;
}
.zone-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.zone-type {
  font-size: 12px;
  color: #606266;
}
.zone-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.zone-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
