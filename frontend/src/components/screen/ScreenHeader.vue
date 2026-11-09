<template>
  <header class="screen-header">
    <div class="sh-left">
      <div class="sh-logo"><el-icon><DataBoard /></el-icon></div>
      <div class="sh-title">
        <h1>智慧工地 AI 安全监测大屏</h1>
        <p>YOLO 视觉识别 · 实时违规监测 · 安全态势总览</p>
      </div>
    </div>

    <div class="sh-right">
      <div class="sh-status">
        <span class="dot" :class="{ off: online <= 0 }"></span>
        在线摄像头 <b>{{ online }}</b>
      </div>
      <div class="sh-status" :class="{ warn: unread > 0 }">
        <el-icon><Bell /></el-icon>
        未读预警 <b>{{ unread }}</b>
      </div>
      <div class="sh-clock">
        <span class="time">{{ clock }}</span>
        <span class="date">{{ today }}</span>
      </div>
      <div class="sh-actions">
        <button class="sh-btn" title="全屏 / 退出全屏" @click="$emit('toggle-fullscreen')">
          <el-icon><FullScreen /></el-icon>{{ isFullscreen ? "退出全屏" : "全屏" }}
        </button>
        <button
          class="sh-btn ghost"
          :class="{ on: rotateOn }"
          :title="rotateOn ? '轮播中：点此停止' : '启动值班轮播（总览 ↔ 告警）'"
          @click="$emit('toggle-rotate')"
        >
          <el-icon><Refresh v-if="rotateOn" /><View v-else /></el-icon>
          {{ rotateOn ? "停止轮播" : "值班轮播" }}
        </button>
        <button class="sh-btn ghost" title="返回后台看板" @click="$emit('exit')">
          <el-icon><Back /></el-icon>返回
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

defineProps<{
  online: number;
  unread: number;
  isFullscreen: boolean;
  rotateOn?: boolean;
}>();
defineEmits<{
  (e: "toggle-fullscreen"): void;
  (e: "toggle-rotate"): void;
  (e: "exit"): void;
}>();

const now = ref(new Date());
let timer: number | null = null;

const pad = (n: number) => String(n).padStart(2, "0");
const clock = computed(
  () =>
    `${pad(now.value.getHours())}:${pad(now.value.getMinutes())}:${pad(
      now.value.getSeconds()
    )}`
);
const week = ["日", "一", "二", "三", "四", "五", "六"];
const today = computed(() => {
  const d = now.value;
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(
    d.getDate()
  )} 星期${week[d.getDay()]}`;
});

onMounted(() => {
  timer = window.setInterval(() => (now.value = new Date()), 1000);
});
onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer);
});
</script>

<style scoped>
.screen-header {
  height: 74px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 26px;
  border-radius: 10px;
  background: linear-gradient(
    90deg,
    rgba(20, 42, 78, 0.75) 0%,
    rgba(10, 22, 43, 0.35) 55%,
    rgba(20, 42, 78, 0.75) 100%
  );
  border: 1px solid rgba(79, 156, 255, 0.25);
  box-shadow: inset 0 0 30px rgba(47, 107, 255, 0.1);
}
.sh-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.sh-logo {
  width: 46px;
  height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #06101f;
  border-radius: 12px;
  background: linear-gradient(135deg, #22d3ee, #2f6bff);
  box-shadow: 0 0 22px rgba(34, 211, 238, 0.55);
}
.sh-title h1 {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 3px;
  color: #eaf3ff;
  text-shadow: 0 0 18px rgba(79, 156, 255, 0.5);
  line-height: 1.2;
}
.sh-title p {
  margin-top: 3px;
  font-size: 12px;
  letter-spacing: 2px;
  color: #5b7194;
}
.sh-right {
  display: flex;
  align-items: center;
  gap: 22px;
}
.sh-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: #9fb3d1;
}
.sh-status b {
  color: #e6f1ff;
  font-size: 17px;
  font-variant-numeric: tabular-nums;
}
.sh-status.warn b {
  color: #f59e0b;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  animation: pulseDot 2s infinite;
}
.dot.off {
  background: #ef4444;
  animation: none;
}
@keyframes pulseDot {
  0% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.55);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(34, 197, 94, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
  }
}
.sh-clock {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.15;
}
.sh-clock .time {
  font-size: 26px;
  font-weight: 700;
  color: #eaf3ff;
  font-variant-numeric: tabular-nums;
  letter-spacing: 1px;
}
.sh-clock .date {
  font-size: 12px;
  color: #5b7194;
  letter-spacing: 1px;
}
.sh-actions {
  display: flex;
  gap: 10px;
}
.sh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
  color: #cfe2ff;
  background: rgba(47, 107, 255, 0.22);
  border: 1px solid rgba(79, 156, 255, 0.35);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.sh-btn:hover {
  background: rgba(47, 107, 255, 0.38);
  box-shadow: 0 0 16px rgba(79, 156, 255, 0.45);
}
.sh-btn.on {
  color: #06101f;
  background: linear-gradient(135deg, #22d3ee, #2f6bff);
  border-color: rgba(34, 211, 238, 0.6);
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.5);
}
.sh-btn.ghost {
  background: transparent;
  color: #9fb3d1;
}
</style>
