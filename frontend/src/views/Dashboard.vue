<template>
  <div v-loading="loading">
    <!-- 关键指标 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num warn">{{ stats.today }}</div>
          <div class="stat-label">今日违规</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num">{{ stats.total }}</div>
          <div class="stat-label">累计违规</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num green">{{ stats.online_cameras }}</div>
          <div class="stat-label">在线摄像头</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-num blue">{{ weekTotal }}</div>
          <div class="stat-label">近 7 天违规</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card>
          <template #header>近 7 天违规趋势</template>
          <div ref="trendRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card>
          <template #header>违规类型分布</template>
          <div ref="typeRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px">
      <template #header>摄像头违规排行</template>
      <div ref="rankRef" class="chart chart-lg"></div>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>系统说明</template>
      <p>本系统基于 YOLO 实现工地安全帽、马甲、口罩的智能识别，自动抓拍违规并生成安全日志。</p>
      <p>技术栈：FastAPI + MySQL + Vue3 + Element Plus + MediaMTX + YOLOv8</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElNotification } from "element-plus";
// 按需引入 ECharts（避免全量包导致路由 chunk 过大）
import { init, use, type ECharts } from "echarts/core";
import { LineChart, BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { getDashboard, type DashboardData } from "@/api/violation";
import { VIOLATION_TYPE_MAP } from "@/constants/violations";

use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const loading = ref(false);
const stats = ref<DashboardData>({
  total: 0,
  today: 0,
  online_cameras: 0,
  trend: [],
  types: [],
  ranking: [],
});
const lastTotal = ref<number | null>(null);

const trendRef = ref<HTMLDivElement | null>(null);
const typeRef = ref<HTMLDivElement | null>(null);
const rankRef = ref<HTMLDivElement | null>(null);

let trendChart: ECharts | null = null;
let typeChart: ECharts | null = null;
let rankChart: ECharts | null = null;
let pollTimer: number | null = null;

const weekTotal = computed(() =>
  stats.value.trend.reduce((sum, p) => sum + p.count, 0)
);

function renderCharts() {
  if (!trendChart || !typeChart || !rankChart) return;

  // 近 7 天趋势
  trendChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: "category",
      data: stats.value.trend.map((p) => p.date.slice(5)),
    },
    yAxis: { type: "value", minInterval: 1 },
    series: [
      {
        name: "违规数",
        type: "line",
        smooth: true,
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: "#f56c6c" },
        data: stats.value.trend.map((p) => p.count),
      },
    ],
  });

  // 类型分布饼图
  const typeData = stats.value.types.map((t) => ({
    name: VIOLATION_TYPE_MAP[t.type] || t.type,
    value: t.count,
  }));
  typeChart.setOption({
    tooltip: { trigger: "item", formatter: "{b}: {c} 条 ({d}%)" },
    legend: { bottom: 0 },
    series: [
      {
        type: "pie",
        radius: ["42%", "68%"],
        center: ["50%", "45%"],
        data: typeData,
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
      },
    ],
  });

  // 摄像头排行
  rankChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 40, top: 16, bottom: 24 },
    xAxis: { type: "value", minInterval: 1 },
    yAxis: {
      type: "category",
      inverse: true,
      data: stats.value.ranking.map((r) => r.name),
    },
    series: [
      {
        name: "违规数",
        type: "bar",
        barMaxWidth: 22,
        itemStyle: { color: "#409eff", borderRadius: [0, 4, 4, 0] },
        data: stats.value.ranking.map((r) => r.count),
      },
    ],
  });
}

async function load(notify: boolean) {
  try {
    loading.value = true;
    const data = await getDashboard();
    // 实时提醒：总违规数增长时弹通知（首次加载不提醒）
    if (notify && lastTotal.value != null && data.total > lastTotal.value) {
      ElNotification({
        title: "新增违规",
        message: `检测到 ${data.total - lastTotal.value} 条新的违规记录`,
        type: "warning",
        duration: 5000,
      });
    }
    lastTotal.value = data.total;
    stats.value = data;
    renderCharts();
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  trendChart = init(trendRef.value!);
  typeChart = init(typeRef.value!);
  rankChart = init(rankRef.value!);
  window.addEventListener("resize", resizeCharts);
  await load(false);
  // 每 15 秒自动刷新 + 新增违规提醒
  pollTimer = window.setInterval(() => load(true), 15000);
});

function resizeCharts() {
  trendChart?.resize();
  typeChart?.resize();
  rankChart?.resize();
}

onBeforeUnmount(() => {
  if (pollTimer) window.clearInterval(pollTimer);
  window.removeEventListener("resize", resizeCharts);
  trendChart?.dispose();
  typeChart?.dispose();
  rankChart?.dispose();
});
</script>

<style scoped>
.stat-card {
  text-align: center;
}
.stat-num {
  font-size: 40px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}
.stat-num.warn {
  color: #f56c6c;
}
.stat-num.green {
  color: #67c23a;
}
.stat-num.blue {
  color: #409eff;
}
.stat-label {
  color: #666;
  margin-top: 6px;
}
.chart {
  height: 300px;
}
.chart-lg {
  height: 320px;
}
</style>
