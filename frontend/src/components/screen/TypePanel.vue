<template>
  <PanelFrame title="违规类型分布" :hint="`近 ${days} 天`">
    <div ref="el" class="chart"></div>
  </PanelFrame>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import PanelFrame from "./PanelFrame.vue";
import { init, type ECharts } from "@/utils/echarts";
import { SCREEN, TOOLTIP, TYPE_COLORS } from "@/constants/screenTheme";
import { VIOLATION_TYPE_MAP } from "@/constants/violations";

const props = defineProps<{ types: { type: string; count: number }[]; days: number }>();

const el = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;
let ro: ResizeObserver | null = null;

const total = computed(() => props.types.reduce((s, t) => s + t.count, 0));

function render() {
  if (!chart) return;
  const data = props.types.map((t) => ({
    name: VIOLATION_TYPE_MAP[t.type] || t.type,
    value: t.count,
    itemStyle: { color: TYPE_COLORS[t.type] || SCREEN.brand },
  }));
  chart.setOption(
    {
      color: SCREEN.palette,
      tooltip: { trigger: "item", formatter: "{b}: {c} 条 ({d}%)", ...TOOLTIP },
      legend: {
        bottom: 0,
        icon: "circle",
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 16,
        textStyle: { color: "#9fb3d1", fontSize: 12 },
      },
      graphic: [
        {
          type: "text",
          left: "center",
          top: "31%",
          style: {
            text: String(total.value),
            fill: "#eaf3ff",
            fontSize: 30,
            fontWeight: 800,
            textAlign: "center",
          },
        },
        {
          type: "text",
          left: "center",
          top: "45%",
          style: {
            text: "违规总数",
            fill: "#5b7194",
            fontSize: 12,
            textAlign: "center",
          },
        },
      ],
      series: [
        {
          type: "pie",
          radius: ["48%", "68%"],
          center: ["50%", "40%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: "rgba(6,12,24,0.9)", borderWidth: 3 },
          label: { show: false },
          labelLine: { show: false },
          emphasis: {
            itemStyle: { shadowBlur: 18, shadowColor: "rgba(79,156,255,0.7)" },
          },
          data,
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

watch(() => props.types, render, { deep: true });

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
</style>
