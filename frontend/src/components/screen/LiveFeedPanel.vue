<template>
  <PanelFrame title="实时抓拍" :hint="latest.length ? `最新 ${latest.length} 条` : ''">
    <template #extra>
      <span class="live-badge"><span class="lb-dot"></span>LIVE</span>
    </template>

    <div v-if="current" class="live-view">
      <transition name="fade" mode="out-in">
        <img
          :key="current.id"
          class="live-img"
          :src="current.anno_url || current.image_url"
          alt="违规抓拍"
        />
      </transition>
      <div class="live-overlay">
        <span class="lv-type" :style="{ background: typeColor(current.violation_type) }">
          {{ typeName(current.violation_type) }}
        </span>
        <div class="lv-text">
          <div class="lv-cam">
            {{ current.camera_name }}
            <span v-if="current.location" class="lv-loc">· {{ current.location }}</span>
          </div>
          <div class="lv-meta">
            <span>{{ current.created_at }}</span>
            <span class="lv-conf">置信度 {{ (current.confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>

      <div class="live-dots">
        <i
          v-for="(v, i) in latest"
          :key="v.id"
          :class="{ on: i === index }"
          @click="index = i"
        ></i>
      </div>
    </div>

    <div v-else class="live-empty">
      <el-icon><Camera /></el-icon>
      <p>暂无抓拍记录</p>
    </div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import PanelFrame from "./PanelFrame.vue";
import { TYPE_COLORS } from "@/constants/screenTheme";
import { VIOLATION_TYPE_MAP } from "@/constants/violations";
import type { LatestViolation } from "@/api/violation";

const props = defineProps<{ latest: LatestViolation[] }>();

const index = ref(0);
let timer: number | null = null;

const current = computed(() => props.latest[index.value] ?? null);

const typeName = (t: string) => VIOLATION_TYPE_MAP[t] || t || "未知";
const typeColor = (t: string) => TYPE_COLORS[t] || "#2f6bff";

function restart() {
  if (timer !== null) window.clearInterval(timer);
  timer = null;
  if (props.latest.length > 1) {
    timer = window.setInterval(() => {
      index.value = (index.value + 1) % props.latest.length;
    }, 5000);
  }
}

watch(
  () => props.latest,
  () => {
    if (index.value >= props.latest.length) index.value = 0;
    restart();
  },
  { deep: true }
);

restart();

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer);
});
</script>

<style scoped>
.live-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  letter-spacing: 1px;
  color: #4ade80;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.14);
  border: 1px solid rgba(34, 197, 94, 0.35);
}
.lb-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: blink 1.4s infinite;
}
@keyframes blink {
  50% {
    opacity: 0.25;
  }
}
.live-view {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(6, 12, 24, 0.7);
}
.live-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.live-overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 34px 14px 12px;
  background: linear-gradient(0deg, rgba(3, 8, 18, 0.92) 0%, rgba(3, 8, 18, 0) 100%);
}
.lv-type {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 0 14px rgba(239, 68, 68, 0.5);
}
.lv-text {
  min-width: 0;
}
.lv-cam {
  font-size: 14px;
  font-weight: 600;
  color: #eaf3ff;
}
.lv-loc {
  font-weight: 400;
  color: #9fb3d1;
  font-size: 12px;
}
.lv-meta {
  display: flex;
  gap: 14px;
  margin-top: 2px;
  font-size: 11.5px;
  color: #7d93b5;
  font-variant-numeric: tabular-nums;
}
.lv-conf {
  color: #67e8f9;
}
.live-dots {
  position: absolute;
  right: 12px;
  top: 10px;
  display: flex;
  gap: 5px;
}
.live-dots i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.35);
  cursor: pointer;
  transition: all 0.2s;
}
.live-dots i.on {
  width: 16px;
  border-radius: 4px;
  background: #22d3ee;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.9);
}
.live-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #3f5578;
  font-size: 13px;
}
.live-empty .el-icon {
  font-size: 34px;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
