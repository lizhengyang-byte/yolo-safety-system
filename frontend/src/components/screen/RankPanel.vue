<template>
  <PanelFrame :title="mode === 'camera' ? '摄像头违规排行' : '点位违规排行'" hint="Top 6">
    <template #extra>
      <div class="seg">
        <button :class="{ on: mode === 'camera' }" @click="mode = 'camera'">摄像头</button>
        <button :class="{ on: mode === 'location' }" @click="mode = 'location'">点位</button>
      </div>
    </template>

    <div class="rank-body">
      <div v-if="!rows.length" class="rank-empty">
        <el-icon><Histogram /></el-icon>
        <p>窗口内暂无违规</p>
      </div>
      <ul v-else class="rank-list">
        <li v-for="(r, i) in rows" :key="r.label + i" class="rank-item">
          <span class="rk-no" :class="'no-' + (i + 1)">{{ i + 1 }}</span>
          <div class="rk-main">
            <div class="rk-top">
              <span class="rk-label">{{ r.label }}</span>
              <span class="rk-val">{{ r.count }}</span>
            </div>
            <div class="rk-track">
              <i :style="{ width: (r.count / max) * 100 + '%' }" :class="mode"></i>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import PanelFrame from "./PanelFrame.vue";

const props = defineProps<{
  ranking: { name: string; count: number }[];
  locationRanking: { location: string; count: number }[];
}>();

const mode = ref<"camera" | "location">("camera");
let timer: number | null = null;

const rows = computed(() => {
  const src =
    mode.value === "camera"
      ? props.ranking.map((r) => ({ label: r.name, count: r.count }))
      : props.locationRanking.map((r) => ({ label: r.location, count: r.count }));
  return src.slice(0, 6);
});
const max = computed(() => Math.max(1, ...rows.value.map((r) => r.count)));

onMounted(() => {
  timer = window.setInterval(() => {
    mode.value = mode.value === "camera" ? "location" : "camera";
  }, 8000);
});
onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer);
});
</script>

<style scoped>
.seg {
  display: inline-flex;
  padding: 2px;
  border-radius: 8px;
  background: rgba(47, 107, 255, 0.14);
  border: 1px solid rgba(79, 156, 255, 0.2);
}
.seg button {
  padding: 3px 10px;
  font-size: 11.5px;
  color: #9fb3d1;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.16s ease;
}
.seg button.on {
  color: #fff;
  background: linear-gradient(135deg, #2f6bff, #4f9cff);
}
.rank-body {
  height: 100%;
  overflow: auto;
}
.rank-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #3f5578;
  font-size: 13px;
}
.rank-empty .el-icon {
  font-size: 30px;
}
.rank-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.rk-no {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  border-radius: 6px;
  color: #9fb3d1;
  background: rgba(255, 255, 255, 0.07);
}
.rk-no.no-1 {
  color: #06101f;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.7);
}
.rk-no.no-2 {
  color: #06101f;
  background: linear-gradient(135deg, #cbd5e1, #94a3b8);
}
.rk-no.no-3 {
  color: #06101f;
  background: linear-gradient(135deg, #f0a97a, #cf7a4a);
}
.rk-main {
  flex: 1;
  min-width: 0;
}
.rk-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.rk-label {
  font-size: 12.5px;
  color: #cbd9ee;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rk-val {
  font-size: 13px;
  font-weight: 700;
  color: #67e8f9;
  font-variant-numeric: tabular-nums;
}
.rk-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(79, 156, 255, 0.1);
  overflow: hidden;
}
.rk-track i {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s ease;
}
.rk-track i.camera {
  background: linear-gradient(90deg, #2f6bff, #22d3ee);
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.6);
}
.rk-track i.location {
  background: linear-gradient(90deg, #f59e0b, #f97316);
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
}
</style>
