<template>
  <div class="cell" :class="{ focused: focused }">
    <video ref="videoRef" autoplay muted playsinline></video>
    <canvas ref="canvasRef"></canvas>
    <div class="badge" :class="camera.status === 'online' ? 'on' : 'off'">
      <span class="dot"></span>{{ camera.status === "online" ? "在线" : "离线" }}
    </div>
    <div class="name">
      {{ camera.name }}<span v-if="camera.location">（{{ camera.location }}）</span>
    </div>
    <div v-if="focused" class="ai-tag"><span class="ai-dot"></span>AI 检测中</div>
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
  background: radial-gradient(circle at 50% 40%, #101826, #05070c);
  border-radius: 14px;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.55), var(--shadow-sm);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.cell.focused {
  border-color: var(--brand-400);
  box-shadow: 0 0 0 2px rgba(79, 156, 255, 0.35), 0 12px 30px rgba(47, 107, 255, 0.28),
    inset 0 0 40px rgba(0, 0, 0, 0.45);
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
  top: 10px;
  right: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 11px 3px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: #fff;
  z-index: 2;
  backdrop-filter: blur(6px);
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.16);
}
.badge .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.badge.on .dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}
.badge.off .dot {
  background: #94a3b8;
}
.name {
  position: absolute;
  left: 10px;
  bottom: 9px;
  padding: 4px 12px;
  border-radius: 9px;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 12.5px;
  z-index: 2;
  max-width: 82%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(47, 107, 255, 0.92), rgba(79, 156, 255, 0.92));
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  z-index: 2;
  box-shadow: 0 6px 16px rgba(47, 107, 255, 0.4);
}
.ai-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
  animation: blink 1.4s infinite;
}
@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.25;
  }
}
.no-flv {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f87171;
  font-size: 14px;
  background: rgba(10, 15, 25, 0.9);
}
</style>
