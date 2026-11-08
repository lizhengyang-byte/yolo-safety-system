<template>
  <div v-loading="loading" class="dashboard">
    <!-- 工具栏：时间范围切换 + PDF 报告导出 -->
    <el-card class="toolbar-card">
      <div class="toolbar-inner">
        <div class="range-box">
          <span class="toolbar-label">统计范围</span>
          <el-radio-group v-model="days" @change="onDaysChange">
            <el-radio-button :label="7">近 7 天</el-radio-button>
            <el-radio-button :label="30">近 30 天</el-radio-button>
            <el-radio-button :label="90">近 90 天</el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-actions">
          <el-button class="screen-entry" @click="openScreen">
            <el-icon class="el-icon--left"><DataBoard /></el-icon>进入智慧大屏
          </el-button>
          <el-dropdown @command="exportReport">
            <el-button type="primary" :loading="exporting">
              导出 PDF 报告<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="week">安全周报（近 7 天）</el-dropdown-item>
                <el-dropdown-item command="month">安全月报（近 30 天）</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-card>

    <!-- 关键指标 -->
    <el-row :gutter="16" class="stat-row">
      <el-col v-for="c in statCards" :key="c.key" :xs="12" :sm="12" :md="6">
        <div class="stat-card" :class="'tone-' + c.tone">
          <div class="stat-glow"></div>
          <div class="stat-ico">
            <el-icon><component :is="c.icon" /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-num tnum">{{ c.value }}</div>
            <div class="stat-label">{{ c.label }}</div>
            <div v-if="c.delta" class="stat-delta" :class="c.delta.up ? 'up' : 'down'">
              {{ c.delta.text }}
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 趋势 + 类型分布 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :md="14">
        <el-card class="panel">
          <template #header>
            <div class="card-head-title">
              <span class="ico"><el-icon><TrendCharts /></el-icon></span>
              违规趋势（近 {{ days }} 天）
            </div>
          </template>
          <div ref="trendRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="10">
        <el-card class="panel">
          <template #header>
            <div class="card-head-title">
              <span class="ico"><el-icon><Odometer /></el-icon></span>
              违规类型分布
            </div>
          </template>
          <div ref="typeRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 排行 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :md="12">
        <el-card class="panel">
          <template #header>
            <div class="card-head-title">
              <span class="ico"><el-icon><Histogram /></el-icon></span>
              摄像头违规排行
            </div>
          </template>
          <div ref="rankRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="panel">
          <template #header>
            <div class="card-head-title">
              <span class="ico"><el-icon><Location /></el-icon></span>
              点位违规排行（跨项目点位统计）
            </div>
          </template>
          <div ref="locRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最新抓拍 -->
    <el-card class="panel latest-card">
      <template #header>
        <div class="card-head-title">
          <span class="ico"><el-icon><Camera /></el-icon></span>
          最新抓拍
          <span class="head-hint">实时同步最近 6 条违规证据图</span>
        </div>
      </template>
      <div v-if="latest.length" class="latest-grid">
        <div v-for="v in latest" :key="v.id" class="latest-item">
          <el-image
            class="latest-img"
            :src="v.anno_url || v.image_url"
            fit="cover"
            :preview-src-list="[v.anno_url || v.image_url]"
            preview-teleported
          />
          <div class="latest-meta">
            <span class="latest-type" :style="{ color: typeColor(v.violation_type) }">
              {{ VIOLATION_TYPE_MAP[v.violation_type] || v.violation_type }}
            </span>
            <span class="latest-cam">{{ v.camera_name }}</span>
            <span class="latest-time">{{ (v.created_at || "").slice(5, 16) }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无抓拍记录" :image-size="70" />
    </el-card>

    <!-- 系统说明 -->
    <el-card class="system-card">
      <div class="system-info">
        <div class="system-mark"><el-icon><Cpu /></el-icon></div>
        <div class="system-text">
          <h3>系统说明</h3>
          <p>
            本系统基于 YOLO 实现工地安全帽、马甲、口罩的智能识别，自动抓拍违规并生成安全日志。
          </p>
          <div class="tech-chips">
            <span>FastAPI</span>
            <span>SQLite / MySQL</span>
            <span>Vue3</span>
            <span>Element Plus</span>
            <span>MediaMTX</span>
            <span>YOLOv8</span>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import axios from "axios";
import { useRouter } from "vue-router";
import { ElMessage, ElNotification } from "element-plus";
import { ArrowDown } from "@element-plus/icons-vue";
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
import { TYPE_COLORS } from "@/constants/screenTheme";
import { downloadBlob, parseFilename } from "@/utils/download";

use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const router = useRouter();
const openScreen = () => router.push("/screen");
const typeColor = (t: string) => TYPE_COLORS[t] || "#2f6bff";

const loading = ref(false);
const days = ref(7);
const exporting = ref(false);
const stats = ref<DashboardData>({
  total: 0,
  today: 0,
  online_cameras: 0,
  trend: [],
  types: [],
  ranking: [],
  location_ranking: [],
});
const lastTotal = ref<number | null>(null);

const trendRef = ref<HTMLDivElement | null>(null);
const typeRef = ref<HTMLDivElement | null>(null);
const rankRef = ref<HTMLDivElement | null>(null);
const locRef = ref<HTMLDivElement | null>(null);

let trendChart: ECharts | null = null;
let typeChart: ECharts | null = null;
let rankChart: ECharts | null = null;
let locChart: ECharts | null = null;
let pollTimer: number | null = null;

const weekTotal = computed(() =>
  stats.value.trend.reduce((sum, p) => sum + p.count, 0)
);
const latest = computed(() => stats.value.latest ?? []);

// KPI 磁贴（含环比徽标）
const statCards = computed(() => {
  const d = stats.value.deltas;
  return [
    {
      key: "today",
      label: "今日违规",
      value: stats.value.today,
      tone: "danger",
      icon: "Warning",
      delta: d
        ? {
            up: d.today_delta > 0,
            text: `较昨日 ${d.today_delta >= 0 ? "+" : ""}${d.today_delta}`,
          }
        : undefined,
    },
    {
      key: "total",
      label: "累计违规",
      value: stats.value.total,
      tone: "brand",
      icon: "Histogram",
      delta: undefined,
    },
    {
      key: "online",
      label: "在线摄像头",
      value: stats.value.online_cameras,
      tone: "success",
      icon: "VideoCamera",
      delta: undefined,
    },
    {
      key: "week",
      label: `近 ${days.value} 天违规`,
      value: weekTotal.value,
      tone: "warning",
      icon: "TrendCharts",
      delta:
        d && d.growth_pct !== null && d.growth_pct !== undefined
          ? {
              up: d.growth_pct > 0,
              text: `环比 ${d.growth_pct >= 0 ? "+" : ""}${d.growth_pct}%`,
            }
          : undefined,
    },
  ];
});

// ---------- 图表统一视觉配置 ----------
const PALETTE = ["#2f6bff", "#22d3ee", "#f59e0b", "#ef4444", "#22c55e", "#8b5cf6"];
const AXIS_LABEL = { color: "#94a3b8", fontSize: 11 };
const AXIS_LINE = { lineStyle: { color: "#e6ebf2" } };
const SPLIT_LINE = { lineStyle: { color: "#eef2f8", type: "dashed" as const } };
const TOOLTIP = {
  backgroundColor: "rgba(15,23,42,0.92)",
  borderWidth: 0,
  padding: [8, 12] as [number, number],
  textStyle: { color: "#fff", fontSize: 12 },
  extraCssText: "border-radius:10px;box-shadow:0 10px 28px rgba(15,23,42,.28);",
};

function barGradient(from: string, to: string) {
  return {
    type: "linear" as const,
    x: 0,
    y: 0,
    x2: 1,
    y2: 0,
    colorStops: [
      { offset: 0, color: from },
      { offset: 1, color: to },
    ],
  };
}

function renderCharts() {
  if (!trendChart || !typeChart || !rankChart || !locChart) return;

  // 违规趋势
  trendChart.setOption({
    tooltip: { trigger: "axis", ...TOOLTIP },
    grid: { left: 44, right: 18, top: 24, bottom: 28 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: stats.value.trend.map((p) => p.date.slice(5)),
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
        lineStyle: { width: 3, color: "#2f6bff" },
        itemStyle: { color: "#2f6bff", borderColor: "#fff", borderWidth: 2 },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(47,107,255,0.30)" },
              { offset: 1, color: "rgba(47,107,255,0.01)" },
            ],
          },
        },
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
    color: PALETTE,
    tooltip: { trigger: "item", formatter: "{b}: {c} 条 ({d}%)", ...TOOLTIP },
    legend: {
      bottom: 0,
      icon: "circle",
      itemWidth: 9,
      itemHeight: 9,
      itemGap: 14,
      textStyle: { color: "#64748b", fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["46%", "70%"],
        center: ["50%", "44%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 8, borderColor: "#fff", borderWidth: 3 },
        label: { show: false },
        labelLine: { show: false },
        data: typeData,
      },
    ],
  });

  // 摄像头排行
  rankChart.setOption({
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...TOOLTIP },
    grid: { left: 8, right: 36, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: AXIS_LABEL,
      splitLine: SPLIT_LINE,
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: stats.value.ranking.map((r) => r.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...AXIS_LABEL, color: "#64748b" },
    },
    series: [
      {
        name: "违规数",
        type: "bar",
        barMaxWidth: 16,
        itemStyle: { borderRadius: [0, 8, 8, 0], color: barGradient("#4f9cff", "#2f6bff") },
        data: stats.value.ranking.map((r) => r.count),
      },
    ],
  });

  // 点位排行（跨项目点位统计）
  locChart.setOption({
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, ...TOOLTIP },
    grid: { left: 8, right: 36, top: 8, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: AXIS_LABEL,
      splitLine: SPLIT_LINE,
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: stats.value.location_ranking.map((r) => r.location),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...AXIS_LABEL, color: "#64748b" },
    },
    series: [
      {
        name: "违规数",
        type: "bar",
        barMaxWidth: 16,
        itemStyle: { borderRadius: [0, 8, 8, 0], color: barGradient("#f59e0b", "#f97316") },
        data: stats.value.location_ranking.map((r) => r.count),
      },
    ],
  });
}

async function load(notify: boolean) {
  try {
    loading.value = true;
    const data = await getDashboard(days.value);
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

function onDaysChange() {
  load(false);
}

/** 导出 PDF 安全报告（周报/月报，后端 reportlab 生成） */
async function exportReport(period: "week" | "month") {
  if (exporting.value) return;
  exporting.value = true;
  try {
    const resp = await axios.get("/api/logs/report", {
      params: { period },
      responseType: "blob",
      headers: { Authorization: `Bearer ${localStorage.getItem("token") || ""}` },
      timeout: 60000,
    });
    const blob = resp.data as Blob;
    if (blob.size < 1000 && (blob.type.includes("json") || blob.type.includes("text"))) {
      // 后端返回了错误 JSON/文本（如 500），读出来提示
      const text = await blob.text();
      throw new Error(text || "导出失败，请稍后重试");
    }
    const filename =
      parseFilename(resp.headers["content-disposition"]) ||
      `safety_report_${period}.pdf`;
    downloadBlob(blob, filename);
    ElMessage.success(`报告导出成功（${(blob.size / 1024).toFixed(1)} KB）`);
  } catch (e) {
    ElMessage.error((e as Error).message || "导出失败，请稍后重试");
  } finally {
    exporting.value = false;
  }
}

onMounted(async () => {
  trendChart = init(trendRef.value!);
  typeChart = init(typeRef.value!);
  rankChart = init(rankRef.value!);
  locChart = init(locRef.value!);
  window.addEventListener("resize", resizeCharts);
  await load(false);
  // 每 15 秒自动刷新 + 新增违规提醒
  pollTimer = window.setInterval(() => load(true), 15000);
});

function resizeCharts() {
  trendChart?.resize();
  typeChart?.resize();
  rankChart?.resize();
  locChart?.resize();
}

onBeforeUnmount(() => {
  if (pollTimer) window.clearInterval(pollTimer);
  window.removeEventListener("resize", resizeCharts);
  trendChart?.dispose();
  typeChart?.dispose();
  rankChart?.dispose();
  locChart?.dispose();
});
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
}
.toolbar-card :deep(.el-card__body) {
  padding: 14px 20px;
}
.toolbar-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.range-box {
  display: flex;
  align-items: center;
  gap: 14px;
}
.toolbar-label {
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.screen-entry {
  background: linear-gradient(135deg, #0b1730, #12233f);
  border: 1px solid rgba(79, 156, 255, 0.4);
  color: #cfe2ff;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
}
.screen-entry:hover {
  color: #fff;
  border-color: #4f9cff;
  background: linear-gradient(135deg, #12233f, #1b3457);
}
.stat-delta {
  margin-top: 4px;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
.stat-delta.up {
  color: var(--danger);
}
.stat-delta.down {
  color: var(--success);
}

/* ---- KPI 磁贴 ---- */
.stat-row {
  margin-top: 16px;
  row-gap: 16px;
}
.stat-card {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease),
    border-color var(--dur) var(--ease);
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: transparent;
}
.stat-glow {
  position: absolute;
  right: -34px;
  top: -34px;
  width: 118px;
  height: 118px;
  border-radius: 50%;
  background: var(--tone-soft);
  opacity: 0.75;
  pointer-events: none;
}
.stat-ico {
  position: relative;
  z-index: 1;
  flex: 0 0 54px;
  width: 54px;
  height: 54px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: #fff;
  background: var(--tone-grad);
  box-shadow: 0 12px 24px -8px var(--tone);
}
.stat-body {
  position: relative;
  z-index: 1;
}
.stat-num {
  font-size: 34px;
  font-weight: 800;
  line-height: 1.05;
  color: var(--text-1);
}
.stat-label {
  color: var(--text-3);
  font-size: 13px;
  margin-top: 5px;
}
.tone-danger {
  --tone: #ef4444;
  --tone-soft: #feecec;
  --tone-grad: linear-gradient(135deg, #ef4444, #f97316);
}
.tone-brand {
  --tone: #2f6bff;
  --tone-soft: #e9f1ff;
  --tone-grad: linear-gradient(135deg, #2f6bff, #4f9cff);
}
.tone-success {
  --tone: #22c55e;
  --tone-soft: #e8f9ef;
  --tone-grad: linear-gradient(135deg, #22c55e, #10b981);
}
.tone-warning {
  --tone: #f59e0b;
  --tone-soft: #fef4e5;
  --tone-grad: linear-gradient(135deg, #f59e0b, #f97316);
}

/* ---- 图表卡片 ---- */
.chart-row {
  margin-top: 16px;
  row-gap: 16px;
}
.panel {
  height: 100%;
}
.chart {
  height: 300px;
}

/* ---- 最新抓拍 ---- */
.latest-card {
  margin-top: 16px;
}
.latest-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.latest-item {
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--surface-soft);
}
.latest-img {
  display: block;
  width: 100%;
  height: 96px;
}
.latest-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px 9px;
}
.latest-type {
  font-size: 13px;
  font-weight: 700;
}
.latest-cam {
  font-size: 12px;
  color: var(--text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.latest-time {
  font-size: 11px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}
@media (max-width: 1100px) {
  .latest-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ---- 系统说明 ---- */
.system-card {
  margin-top: 16px;
}
.system-info {
  display: flex;
  align-items: flex-start;
  gap: 18px;
}
.system-mark {
  flex: 0 0 52px;
  width: 52px;
  height: 52px;
  border-radius: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: var(--brand-500);
  background: linear-gradient(135deg, var(--brand-100), #eef4ff);
}
.system-text h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 6px;
}
.system-text p {
  color: var(--text-2);
  font-size: 13.5px;
  line-height: 1.7;
}
.tech-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.tech-chips span {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--brand-600);
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--brand-100);
}

@media (max-width: 768px) {
  .chart {
    height: 260px;
  }
  .stat-num {
    font-size: 26px;
  }
  .stat-ico {
    width: 44px;
    height: 44px;
    flex-basis: 44px;
    font-size: 20px;
  }
}
</style>
