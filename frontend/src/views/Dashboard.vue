<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-num">{{ stats.total }}</div>
          <div class="stat-label">违规记录总数</div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card>
          <template #header>违规类型分布</template>
          <el-table :data="typeTable" size="small">
            <el-table-column prop="name" label="违规类型" />
            <el-table-column prop="count" label="数量" />
            <el-table-column label="占比">
              <template #default="{ row }">
                {{ stats.total ? ((row.count / stats.total) * 100).toFixed(1) + "%" : "0%" }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>系统说明</template>
      <p>本系统基于 YOLO 实现工地安全帽、马甲、口罩的智能识别，自动抓拍违规并生成安全日志。</p>
      <p>技术栈：FastAPI + MySQL + Vue3 + Element Plus + MediaMTX + YOLOv8</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getStats } from "@/api/violation";

const stats = ref<{ total: number; detail: { type: string; count: number }[] }>({
  total: 0,
  detail: [],
});

const typeMap: Record<string, string> = {
  no_helmet: "未戴安全帽",
  no_vest: "未穿安全马甲",
  no_mask: "未戴口罩",
};

const typeTable = computed(() =>
  stats.value.detail.map((d) => ({
    name: typeMap[d.type] || d.type,
    count: d.count,
  }))
);

onMounted(async () => {
  stats.value = await getStats();
});
</script>

<style scoped>
.stat-card {
  text-align: center;
}
.stat-num {
  font-size: 42px;
  font-weight: bold;
  color: #409eff;
}
.stat-label {
  color: #666;
  margin-top: 8px;
}
</style>
