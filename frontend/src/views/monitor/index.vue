<template>
  <el-card class="monitor-card">
    <template #header>
      <div class="card-head-row">
        <div class="card-head-title">
          <span class="ico"><el-icon><VideoCamera /></el-icon></span>
          实时监控预览（AI 叠加）
        </div>
        <div class="actions">
          <el-select
            v-model="selectedIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择摄像头（最多 4 路）"
            :multiple-limit="4"
            class="cam-select"
            @change="onSelect"
          >
            <el-option
              v-for="c in cameras"
              :key="c.id"
              :label="`${c.name}（${c.status === 'online' ? '在线' : '离线'}）`"
              :value="c.id"
              :disabled="!c.enabled"
            />
          </el-select>
          <el-switch v-model="autoRotate" active-text="自动轮播" inactive-text="" />
          <el-button @click="toggleFullscreen">
            <el-icon class="btn-ico"><FullScreen /></el-icon>全屏
          </el-button>
        </div>
      </div>
    </template>

    <el-alert
      class="monitor-tip"
      title="AI 叠加：检测框由后端 YOLO 实时识别绘制（与临时演示同一套逻辑），无违规时不入库；FLV 地址前缀可通过 frontend/.env 的 VITE_MEDIAMTX_BASE 配置。"
      type="info"
      :closable="false"
    />

    <div ref="gridRef" class="grid" :class="{ 'grid-multi': selected.length > 1 }">
      <MonitorCell
        v-for="cam in selected"
        :key="cam.id"
        ref="cellRefs"
        :camera="cam"
        :focused="cam.id === focusId"
        :flv-base="flvBase"
      />
      <el-empty
        v-if="!selected.length"
        description="请选择摄像头查看实时画面（需 MediaMTX 运行中）"
        class="empty-grid"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { listCameras, type Camera } from "@/api/camera";
import { demoDetect } from "@/api/demo";
import { listZones } from "@/api/zone";
import { drawDetections } from "@/utils/draw";
import MonitorCell from "./MonitorCell.vue";

// MediaMTX FLV 地址前缀：默认 localhost，可通过 frontend/.env 的 VITE_MEDIAMTX_BASE 配置
const flvBase = import.meta.env.VITE_MEDIAMTX_BASE || "http://localhost:8080";

const cameras = ref<Camera[]>([]);
const selectedIds = ref<number[]>([]);
const focusId = ref<number | null>(null);
const autoRotate = ref(false);
const cellRefs = ref<InstanceType<typeof MonitorCell>[]>([]);
const gridRef = ref<HTMLDivElement | null>(null);
// 当前聚焦摄像头的危险区域（叠加显示用）
const zoneOverlay = ref<{ zone_name: string; polygon: number[][] }[]>([]);

const selected = computed(() =>
  cameras.value.filter((c) => selectedIds.value.includes(c.id))
);

let detectTimer: number | null = null;
let rotateTimer: number | null = null;
let statusTimer: number | null = null;
let inFlight = false;
let paused = false;

// ---------- 摄像头列表与状态 ----------
async function loadCameras() {
  try {
    cameras.value = await listCameras();
  } catch {
    /* 后端暂不可用时静默，轮询会重试 */
  }
}

// ---------- 选择 / 轮播 ----------
function onSelect() {
  if (selectedIds.value.length === 0) {
    focusId.value = null;
    return;
  }
  if (!focusId.value || !selectedIds.value.includes(focusId.value)) {
    focusId.value = selectedIds.value[0];
  }
}

function rotateNext() {
  if (selectedIds.value.length < 2) return;
  const idx = selectedIds.value.indexOf(focusId.value ?? selectedIds.value[0]);
  focusId.value = selectedIds.value[(idx + 1) % selectedIds.value.length];
}

// ---------- 危险区域叠加（按聚焦摄像头拉取） ----------
async function loadZoneOverlay() {
  if (focusId.value == null) {
    zoneOverlay.value = [];
    return;
  }
  try {
    const zones = await listZones(focusId.value);
    zoneOverlay.value = zones
      .filter((z) => z.enabled)
      .map((z) => ({ zone_name: z.zone_name, polygon: z.polygon }));
  } catch {
    zoneOverlay.value = [];
  }
}

watch(focusId, () => {
  loadZoneOverlay();
});

// ---------- AI 叠加检测（复用演示模式检测接口，no_save 不入库） ----------
async function detectLoop() {
  if (paused || inFlight || !focusId.value) return;
  const cell = cellRefs.value.find((c) => c.camera.id === focusId.value);
  if (!cell || !cell.videoReady || !cell.videoEl || !cell.canvasEl) return;

  const video = cell.videoEl;
  const canvas = cell.canvasEl;
  if (canvas.width !== video.videoWidth) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  inFlight = true;
  canvas.toBlob(async (blob) => {
    if (!blob) {
      inFlight = false;
      return;
    }
    try {
      const res = await demoDetect(blob, { noSave: true });
      drawDetections(canvas, res.detections, res.violations, false, zoneOverlay.value);
    } catch {
      /* 检测失败（如模型未就绪）时保留视频画面 */
    } finally {
      inFlight = false;
    }
  }, "image/jpeg", 0.7);
}

// ---------- 全屏 ----------
function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  } else {
    gridRef.value?.requestFullscreen?.().catch(() => {});
  }
}

onMounted(async () => {
  await loadCameras();
  detectTimer = window.setInterval(detectLoop, 600);
  rotateTimer = window.setInterval(() => {
    if (autoRotate.value) rotateNext();
  }, 8000);
  // 摄像头在线状态自动刷新
  statusTimer = window.setInterval(loadCameras, 10000);
  document.addEventListener("visibilitychange", onVisibility);
});

function onVisibility() {
  paused = document.hidden;
  if (!document.hidden) detectLoop();
}

onBeforeUnmount(() => {
  if (detectTimer) window.clearInterval(detectTimer);
  if (rotateTimer) window.clearInterval(rotateTimer);
  if (statusTimer) window.clearInterval(statusTimer);
  document.removeEventListener("visibilitychange", onVisibility);
});
</script>

<style scoped>
.monitor-card :deep(.el-card__body) {
  padding: 18px 20px 20px;
}
.card-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.card-head-title {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-weight: 600;
  color: var(--text-1);
}
.card-head-title .ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--brand-100), #eef4ff);
  color: var(--brand-500);
  font-size: 15px;
}
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.cam-select {
  width: 320px;
}
.btn-ico {
  margin-right: 4px;
}
.monitor-tip {
  margin-bottom: 16px;
  border-radius: var(--radius);
}
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}
.grid-multi {
  grid-template-columns: repeat(2, 1fr);
}
.empty-grid {
  grid-column: 1 / -1;
  padding: 60px 0;
}
@media (max-width: 900px) {
  .grid-multi {
    grid-template-columns: 1fr;
  }
  .cam-select {
    width: 100%;
  }
}
</style>
