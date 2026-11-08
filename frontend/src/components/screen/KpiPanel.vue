<template>
  <PanelFrame title="核心指标" hint="实时">
    <div class="kpi-grid">
      <div v-for="c in cards" :key="c.key" class="kpi-item" :class="'tone-' + c.tone">
        <div class="kpi-top">
          <span class="kpi-ico"><el-icon><component :is="c.icon" /></el-icon></span>
          <span class="kpi-label">{{ c.label }}</span>
        </div>
        <div class="kpi-num"><CountUp :value="c.value" /></div>
        <div v-if="c.delta" class="kpi-delta" :class="c.delta.up ? 'up' : 'down'">
          <span class="arrow">{{ c.delta.up ? "▲" : "▼" }}</span>{{ c.delta.text }}
        </div>
        <div v-else class="kpi-sub">{{ c.sub }}</div>
      </div>
    </div>

    <div class="kpi-foot">
      <span class="kf-label">平均识别置信度</span>
      <div class="kf-bar"><i :style="{ width: confPct + '%' }"></i></div>
      <span class="kf-val">{{ confPct.toFixed(1) }}%</span>
    </div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed } from "vue";
import PanelFrame from "./PanelFrame.vue";
import CountUp from "./CountUp.vue";
import type { DashboardDelta } from "@/api/violation";

const props = defineProps<{
  today: number;
  total: number;
  online: number;
  totalCameras: number;
  weekTotal: number;
  days: number;
  deltas?: DashboardDelta;
  avgConfidence?: number;
}>();

const confPct = computed(() => Math.max(0, Math.min(100, (props.avgConfidence ?? 0) * 100)));

const cards = computed(() => {
  const d = props.deltas;
  return [
    {
      key: "today",
      label: "今日违规",
      value: props.today,
      tone: "danger",
      icon: "Warning",
      delta: d
        ? {
            up: d.today_delta > 0,
            text: `${d.today_delta >= 0 ? "+" : ""}${d.today_delta} 较昨日`,
          }
        : undefined,
      sub: "",
    },
    {
      key: "total",
      label: "累计违规",
      value: props.total,
      tone: "brand",
      icon: "Histogram",
      delta: undefined,
      sub: `历史累计记录`,
    },
    {
      key: "online",
      label: "在线摄像头",
      value: props.online,
      tone: "success",
      icon: "VideoCamera",
      delta: undefined,
      sub: `共 ${props.totalCameras} 路接入`,
    },
    {
      key: "week",
      label: `近 ${props.days} 天违规`,
      value: props.weekTotal,
      tone: "warning",
      icon: "TrendCharts",
      delta:
        d && d.growth_pct !== null
          ? {
              up: d.growth_pct > 0,
              text: `${d.growth_pct >= 0 ? "+" : ""}${d.growth_pct}% 环比`,
            }
          : undefined,
      sub: "统计窗口内合计",
    },
  ];
});
</script>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.kpi-item {
  position: relative;
  padding: 12px 14px 10px;
  border-radius: 8px;
  background: rgba(12, 27, 51, 0.55);
  border: 1px solid rgba(79, 156, 255, 0.14);
  overflow: hidden;
}
.kpi-item::after {
  content: "";
  position: absolute;
  right: -20px;
  top: -20px;
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: var(--tone-soft);
  opacity: 0.22;
}
.kpi-top {
  display: flex;
  align-items: center;
  gap: 7px;
}
.kpi-ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  font-size: 13px;
  color: #fff;
  background: var(--tone-grad);
  box-shadow: 0 0 12px var(--tone-soft);
}
.kpi-label {
  font-size: 12.5px;
  color: #9fb3d1;
}
.kpi-num {
  margin-top: 6px;
  font-size: 32px;
  font-weight: 800;
  line-height: 1.05;
  color: var(--tone);
  text-shadow: 0 0 16px var(--tone-soft);
}
.kpi-delta {
  margin-top: 5px;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}
.kpi-delta .arrow {
  margin-right: 3px;
  font-size: 9px;
}
.kpi-delta.up {
  color: #ef4444;
}
.kpi-delta.down {
  color: #22c55e;
}
.kpi-sub {
  margin-top: 5px;
  font-size: 11.5px;
  color: #5b7194;
}
.tone-danger {
  --tone: #ff6b6b;
  --tone-soft: rgba(239, 68, 68, 0.5);
  --tone-grad: linear-gradient(135deg, #ef4444, #f97316);
}
.tone-brand {
  --tone: #63a4ff;
  --tone-soft: rgba(47, 107, 255, 0.55);
  --tone-grad: linear-gradient(135deg, #2f6bff, #4f9cff);
}
.tone-success {
  --tone: #4ade80;
  --tone-soft: rgba(34, 197, 94, 0.5);
  --tone-grad: linear-gradient(135deg, #22c55e, #10b981);
}
.tone-warning {
  --tone: #fbbf24;
  --tone-soft: rgba(245, 158, 11, 0.5);
  --tone-grad: linear-gradient(135deg, #f59e0b, #f97316);
}
.kpi-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(79, 156, 255, 0.16);
}
.kf-label {
  font-size: 12px;
  color: #9fb3d1;
  white-space: nowrap;
}
.kf-bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: rgba(79, 156, 255, 0.14);
  overflow: hidden;
}
.kf-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #22d3ee, #2f6bff);
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.7);
  transition: width 0.6s ease;
}
.kf-val {
  font-size: 13px;
  font-weight: 700;
  color: #67e8f9;
  font-variant-numeric: tabular-nums;
}
</style>
