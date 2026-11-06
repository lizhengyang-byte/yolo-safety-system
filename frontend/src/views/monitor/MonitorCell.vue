<template>
  <div class="cell" :class="{ focused: focused }">
    <video ref="videoRef" autoplay muted playsinline></video>
    <canvas ref="canvasRef"></canvas>
    <div class="badge" :class="camera.status === 'online' ? 'on' : 'off'">
      {{ camera.status === "online" ? "在线" : "离线" }}
    </div>
    <div class="name">
      {{ camera.name }}<span v-if="camera.location">（{{ camera.location }}）</span>
    </div>
    <div v-if="focused" class="ai-tag">AI 检测中…</div>
    <div v-if="!flvSupported" class="no-flv">当前浏览器不支持 flv.js，请使用 Chrome / Edge</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import flvjs from "flv.js";
import type { Camera } from "@/api/camera";

const props = defineProps<{
  camera: Camera;
  focused: boolean;
  flvBase: string;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const flvSupported = flvjs.isSupported();
let player: any = null;

const videoEl = computed(() => videoRef.value);
const canvasEl = computed(() => canvasRef.value);
const videoReady = computed(
  () => !!videoRef.value && videoRef.value.readyState >= 2 && videoRef.value.videoWidth > 0
);

function buildFlvUrl(id: number): string {
  const base = props.flvBase.replace(/\/+$/, "");
  return `${base}/live/${id}.flv`;
}

function destroyPlayer() {
  if (player) {
    try {
      player.destroy();
    } catch {
      /* 忽略销毁异常 */
    }
    player = null;
  }
}

function createPlayer() {
  destroyPlayer();
  const video = videoRef.value;
  if (!video || !flvSupported) return;
  // 切换摄像头时清空旧画面与画布
  video.srcObject = null;
  video.removeAttribute("src");
  const canvas = canvasRef.value;
  if (canvas) {
    const ctx = canvas.getContext("2d");
    ctx?.clearRect(0, 0, canvas.width, canvas.height);
  }
  player = flvjs.createPlayer({
    type: "flv",
    url: buildFlvUrl(props.camera.id),
    isLive: true,
    hasAudio: false,
  });
  player.attachMediaElement(video);
  player.load();
  player.play().catch(() => {
    /* 断流时静默，状态角标会提示 */
  });
}

onMounted(createPlayer);
watch(() => props.camera.id, createPlayer);
onBeforeUnmount(destroyPlayer);

defineExpose({ videoEl, canvasEl, videoReady, camera: props.camera });
</script>

<style scoped>
.cell {
  position: relative;
  background: #000;
  border-radius: 6px;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  border: 2px solid transparent;
}
.cell.focused {
  border-color: #409eff;
  box-shadow: 0 0 0 1px #409eff;
}
video,
canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  color: #fff;
  z-index: 2;
}
.badge.on {
  background: #67c23a;
}
.badge.off {
  background: #909399;
}
.name {
  position: absolute;
  left: 8px;
  bottom: 6px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 13px;
  z-index: 2;
  max-width: 80%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(64, 158, 255, 0.85);
  color: #fff;
  font-size: 12px;
  z-index: 2;
  animation: pulse 1.6s infinite;
}
.no-flv {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f56c6c;
  font-size: 14px;
  background: #1f1f1f;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
</style>
