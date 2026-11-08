<template>
  <PanelFrame title="违规趋势" :hint="hint">
    <template #extra>
      <div class="seg">
        <button :class="{ on: mode === 'day' }" @click="mode = 'day'">按天</button>
        <button :class="{ on: mode === 'hour' }" @click="mode = 'hour'">今日时段</button>
      </div>
    </template>
    <div ref="el" class="chart"></div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import PanelFrame from "./PanelFrame.vue";
import { init, type ECharts } from "@/utils/echarts";
import { AXIS_LABEL, AXIS_LINE, SCREEN, SPLIT_LINE, TOOLTIP } from "@/constants/screenTheme";
import type { DashboardDelta, HourPoint, TrendPoint } from "@/api/violation";

const props = defineProps<{
  trend: TrendPoint[];
  hourly?: HourPoint[];
  days: number;
  deltas?: DashboardDelta;
}>();

const mode = ref<"day" | "hour">("day");
const el = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;
let ro: ResizeObserver | null = null;

const hint = computed(() => {
  const g = props.deltas?.growth_pct;
  if (g === null || g === undefined) return `近 ${props.days} 天`;
  return `环比 ${g >= 0 ? "+" : ""}${g}%`;
});

function render() {
  if (!chart) return;
  if (mode.value === "hour") {
    const hourly = props.hourly ?? [];
    const max = Math.max(1, ...hourly.map((h) => h.count));
    chart.setOption(
      {
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...TOOLTIP },
        grid: { left: 44, right: 20, top: 26, bottom: 30 },
        xAxis: {
          type: "category",
          data: hourly.map((h) => `${h.hour}`),
          axisLine: AXIS_LINE,
          axisTick: { show: false },
          axisLabel: { ...AXIS_LABEL, interval: 2, formatter: "{value}时" },
        },
        yAxis: {
          type: "value",
          minInterval: 1,
          max,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: AXIS_LABEL,
          splitLine: SPLIT_LINE,
        },
        series: [
          {
            name: "违规数",
            type: "bar",
            barWidth: "52%",
            itemStyle: {
              borderRadius: [4, 4, 0, 0],
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: "#22d3ee" },
                  { offset: 1, color: "rgba(47,107,255,0.25)" },
                ],
              },
            },
            data: hourly.map((h) => h.count),
          },
        ],
      },
      true
    );
    return;
  }

  const dates = props.trend.map((p) => p.date.slice(5));
  const counts = props.trend.map((p) => p.count);
  chart.setOption(
    {
      tooltip: { trigger: "axis", ...TOOLTIP },
      grid: { left: 44, right: 20, top: 26, bottom: 30 },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: dates,
        axisLine: AXIS_LINE,
        axisTick: { show: false },
        axisLabel: AXIS_LABEL,
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: AXIS_LABEL,
        splitLine: SPLIT_LINE,
      },
      series: [
        {
          name: "违规数",
          type: "line",
          smooth: true,
          symbol: "circle",
          symbolSize: 7,
          showSymbol: false,
          lineStyle: { width: 3, color: SCREEN.brand },
          itemStyle: { color: SCREEN.brand, borderColor: "#06101f", borderWidth: 2 },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(47,107,255,0.42)" },
                { offset: 1, color: "rgba(47,107,255,0.02)" },
              ],
            },
          },
          data: counts,
        },
      ],
    },
    true
  );
}

onMounted(() => {
  if (!el.value) return;
  chart = init(el.value);
  render();
  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(el.value);
});

watch([() => props.trend, () => props.hourly, mode], render, { deep: true });

onBeforeUnmount(() => {
  ro?.disconnect();
  chart?.dispose();
});
</script>

<style scoped>
.chart {
  width: 100%;
  height: 100%;
}
.seg {
  display: inline-flex;
  padding: 2px;
  border-radius: 8px;
  background: rgba(47, 107, 255, 0.14);
  border: 1px solid rgba(79, 156, 255, 0.2);
}
.seg button {
  padding: 4px 12px;
  font-size: 12px;
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
  box-shadow: 0 0 12px rgba(79, 156, 255, 0.5);
}
</style>
