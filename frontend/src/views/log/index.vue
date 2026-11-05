<template>
  <el-card>
    <template #header>
      <div class="header">
        <span>安全日志管理</span>
        <div>
          <el-date-picker
            v-model="range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="margin-right: 12px"
          />
          <el-button type="primary" @click="exportExcel">导出 Excel</el-button>
        </div>
      </div>
    </template>

    <el-alert
      title="违规记录自动生成安全日志，支持按时间段导出为 Excel 安全台账（后端用 pandas 生成）。"
      type="success"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-table :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="camera_name" label="摄像头" />
      <el-table-column label="违规类型" width="140">
        <template #default="{ row }">
          {{ typeMap[row.violation_type] || row.violation_type }}
        </template>
      </el-table-column>
      <el-table-column prop="confidence" label="置信度" width="90" />
      <el-table-column prop="created_at" label="抓拍时间" width="180" />
      <el-table-column prop="image_url" label="图片地址" show-overflow-tooltip />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { listViolations, type Violation } from "@/api/violation";

const items = ref<Violation[]>([]);
const range = ref<[string, string] | null>(null);

const typeMap: Record<string, string> = {
  no_helmet: "未戴安全帽",
  no_vest: "未穿马甲",
  no_mask: "未戴口罩",
};

async function load() {
  const res = await listViolations({ page: 1, page_size: 100 });
  items.value = res.items;
}

function exportExcel() {
  const params = new URLSearchParams();
  if (range.value && range.value.length === 2) {
    params.set("start", range.value[0]);
    params.set("end", range.value[1]);
  }
  const token = localStorage.getItem("token") || "";
  window.open(`/api/logs/export?${params.toString()}`);
}

onMounted(load);
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
