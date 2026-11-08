<template>
  <PanelFrame title="摄像头状态" :hint="`${online}/${total} 在线`">
    <template #extra>
      <span class="cs-pill" :class="{ good: online === total && total > 0 }">
        可用率 {{ total ? Math.round((online / total) * 100) : 0 }}%
      </span>
    </template>

    <div class="cs-body">
      <div v-if="!cameras.length" class="cs-empty">
        <el-icon><VideoCamera /></el-icon>
        <p>暂无接入摄像头</p>
      </div>
      <ul v-else class="cs-list">
        <li v-for="c in cameras" :key="c.id" class="cs-item">
          <span class="cs-dot" :class="c.status === 'online' ? 'on' : 'off'"></span>
          <div class="cs-main">
            <div class="cs-name">
              {{ c.name }}
              <span v-if="c.location" class="cs-loc">{{ c.location }}</span>
            </div>
            <div class="cs-state">
              {{ c.status === "online" ? "在线" : "离线" }}
              <span v-if="!c.enabled" class="cs-disabled">· 已停用</span>
            </div>
          </div>
          <div class="cs-count">
            <b>{{ c.recent_count }}</b>
            <span>窗口违规</span>
          </div>
        </li>
      </ul>
    </div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed } from "vue";
import PanelFrame from "./PanelFrame.vue";
import type { CameraStatusItem } from "@/api/violation";

const props = defineProps<{ cameras: CameraStatusItem[] }>();

const total = computed(() => props.cameras.length);
const online = computed(() => props.cameras.filter((c) => c.status === "online").length);
</script>

<style scoped>
.cs-pill {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: 999px;
  color: #9fb3d1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-variant-numeric: tabular-nums;
}
.cs-pill.good {
  color: #4ade80;
  background: rgba(34, 197, 94, 0.14);
  border-color: rgba(34, 197, 94, 0.35);
}
.cs-body {
  height: 100%;
  overflow: auto;
}
.cs-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #3f5578;
  font-size: 13px;
}
.cs-empty .el-icon {
  font-size: 32px;
}
.cs-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.cs-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(12, 27, 51, 0.5);
  border: 1px solid rgba(79, 156, 255, 0.12);
}
.cs-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.cs-dot.on {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.9);
}
.cs-dot.off {
  background: #ef4444;
}
.cs-main {
  flex: 1;
  min-width: 0;
}
.cs-name {
  font-size: 13px;
  font-weight: 600;
  color: #dbe9ff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cs-loc {
  font-weight: 400;
  font-size: 11.5px;
  color: #5b7194;
  margin-left: 4px;
}
.cs-state {
  font-size: 11px;
  color: #7d93b5;
  margin-top: 1px;
}
.cs-disabled {
  color: #5b7194;
}
.cs-count {
  flex-shrink: 0;
  text-align: right;
  line-height: 1.15;
}
.cs-count b {
  display: block;
  font-size: 16px;
  color: #67e8f9;
  font-variant-numeric: tabular-nums;
}
.cs-count span {
  font-size: 10px;
  color: #5b7194;
}
</style>
