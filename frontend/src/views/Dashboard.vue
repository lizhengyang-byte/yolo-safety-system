<template>
  <div v-loading="loading">
    <!-- 工具栏：时间范围切换 + PDF 报告导出 -->
    <el-card class="toolbar">
      <div class="toolbar-inner">
        <div>
          <span class="toolbar-label">统计范围</span>
          <el-radio-group v-model="days" @change="onDaysChange">
            <el-radio-button :label="7">近 7 天</el-radio-button>
            <el-radio-button :label="30">近 30 天</el-radio-button>
            <el-radio-button :label="90">近 90 天</el-radio-button>
          </el-radio-group>
        </div>
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
    </el-card>

    <!-- 关键指标 -->
    <el-row :gutter="16" style="margin-top: 16px">
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
          <div class="stat-label">近 {{ days }} 天违规</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card>
          <template #header>违规趋势（近 {{ days }} 天）</template>
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

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card>
          <template #header>摄像头违规排行</template>
          <div ref="rankRef" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>点位违规排行（跨项目点位统计）</template>
          <div ref="locRef" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px">
      <template #header>系统说明</template>
      <p>本系统基于 YOLO 实现工地安全帽、马甲、口罩的智能识别，自动抓拍违规并生成安全日志。</p>
      <p>技术栈：FastAPI + MySQL + Vue3 + Element Plus + MediaMTX + YOLOv8</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import axios from "axios";
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
import { downloadBlob, parseFilename } from "@/utils/download";

use([LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

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

function renderCharts() {
  if (!trendChart || !typeChart || !rankChart || !locChart) return;

  // 违规趋势
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

  // 点位排行（跨项目点位统计）
  locChart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 40, right: 40, top: 16, bottom: 24 },
    xAxis: { type: "value", minInterval: 1 },
    yAxis: {
      type: "category",
      inverse: true,
      data: stats.value.location_ranking.map((r) => r.location),
    },
    series: [
      {
        name: "违规数",
        type: "bar",
        barMaxWidth: 22,
        itemStyle: { color: "#e6a23c", borderRadius: [0, 4, 4, 0] },
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
.toolbar {
  padding: 4px 0;
}
.toolbar-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.toolbar-label {
  margin-right: 12px;
  color: #666;
  font-size: 14px;
}
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
</style>
