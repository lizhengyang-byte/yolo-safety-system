<template>
  <PanelFrame title="最新预警" :hint="summary ? `今日 ${summary.today} 条` : ''">
    <template #extra>
      <span class="alarm-badge" :class="{ on: unread > 0 }">
        <el-icon><Bell /></el-icon>{{ unread }}
      </span>
    </template>

    <div class="alert-body">
      <div v-if="!items.length" class="alert-empty">
        <el-icon><CircleCheck /></el-icon>
        <p>暂无预警，运行平稳</p>
      </div>
      <ul v-else class="alert-list">
        <li v-for="w in items" :key="w.id" class="alert-item" :class="{ unread: !w.is_read }">
          <span class="ai-dot"></span>
          <div class="ai-main">
            <div class="ai-top">
              <span class="ai-type">{{ typeName(w.violation_type) }}</span>
              <span class="ai-count">×{{ w.count }}</span>
            </div>
            <div class="ai-meta">
              <span class="ai-cam">{{ w.camera_name }}</span>
              <span class="ai-time">{{ shortTime(w.triggered_at) }}</span>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed } from "vue";
import PanelFrame from "./PanelFrame.vue";
import { VIOLATION_TYPE_MAP } from "@/constants/violations";
import type { WarningSummary } from "@/api/violation";

const props = defineProps<{ summary?: WarningSummary }>();

const items = computed(() => props.summary?.latest ?? []);
const unread = computed(() => props.summary?.unread ?? 0);
const typeName = (t: string) => VIOLATION_TYPE_MAP[t] || t || "预警";
const shortTime = (s: string) => (s ? s.slice(5, 16) : "");
</script>

<style scoped>
.alarm-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 9px;
  border-radius: 999px;
  color: #9fb3d1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-variant-numeric: tabular-nums;
}
.alarm-badge.on {
  color: #fca5a5;
  background: rgba(239, 68, 68, 0.16);
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.35);
}
.alert-body {
  height: 100%;
  overflow: auto;
}
.alert-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #3f5578;
  font-size: 13px;
}
.alert-empty .el-icon {
  font-size: 32px;
  color: #22c55e;
}
.alert-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 2px;
}
.alert-item {
  display: flex;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  background: rgba(12, 27, 51, 0.5);
  border: 1px solid rgba(79, 156, 255, 0.12);
}
.alert-item.unread {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(59, 20, 30, 0.35);
}
.ai-dot {
  flex-shrink: 0;
  width: 7px;
  height: 7px;
  margin-top: 6px;
  border-radius: 50%;
  background: #4a5d7c;
}
.alert-item.unread .ai-dot {
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.9);
}
.ai-main {
  flex: 1;
  min-width: 0;
}
.ai-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.ai-type {
  font-size: 13.5px;
  font-weight: 600;
  color: #e6f1ff;
}
.ai-count {
  font-size: 13px;
  font-weight: 700;
  color: #f59e0b;
  font-variant-numeric: tabular-nums;
}
.ai-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 3px;
  font-size: 11.5px;
  color: #7d93b5;
}
.ai-cam {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}
.ai-time {
  font-variant-numeric: tabular-nums;
}
</style>
