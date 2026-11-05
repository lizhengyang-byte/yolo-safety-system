<template>
  <el-card>
    <template #header>
      <div class="header">
        <span>违规抓拍记录</span>
        <el-button type="primary" @click="load">刷新</el-button>
      </div>
    </template>

    <!-- 筛选 -->
    <el-form inline>
      <el-form-item label="违规类型">
        <el-select v-model="query.violation_type" clearable placeholder="全部" style="width: 160px">
          <el-option label="未戴安全帽" value="no_helmet" />
          <el-option label="未穿马甲" value="no_vest" />
          <el-option label="未戴口罩" value="no_mask" />
        </el-select>
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="query.start" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="query.end" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="items" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="camera_name" label="摄像头" />
      <el-table-column label="违规类型" width="140">
        <template #default="{ row }">
          <el-tag :type="tagType(row.violation_type)">
            {{ typeMap[row.violation_type] || row.violation_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置信度" width="100">
        <template #default="{ row }"> {{ (row.confidence * 100).toFixed(1) }}% </template>
      </el-table-column>
      <el-table-column prop="created_at" label="抓拍时间" width="180" />
      <el-table-column label="抓拍图片" width="110">
        <template #default="{ row }">
          <el-image
            v-if="row.image_url"
            :src="row.image_url"
            :preview-src-list="[row.image_url]"
            fit="cover"
            style="width: 80px; height: 50px; border-radius: 4px"
            preview-teleported
          />
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      style="margin-top: 16px; justify-content: flex-end"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="query.page_size"
      :current-page="query.page"
      @current-change="onPage"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { listViolations, type Violation } from "@/api/violation";

const items = ref<Violation[]>([]);
const total = ref(0);
const query = reactive({
  page: 1,
  page_size: 20,
  violation_type: "" as string,
  start: "" as string,
  end: "" as string,
});

const typeMap: Record<string, string> = {
  no_helmet: "未戴安全帽",
  no_vest: "未穿马甲",
  no_mask: "未戴口罩",
};

function tagType(type: string) {
  if (type === "no_helmet") return "danger";
  if (type === "no_vest") return "warning";
  return "info";
}

async function load() {
  const res = await listViolations(query);
  items.value = res.items;
  total.value = res.total;
}

function reset() {
  query.page = 1;
  query.violation_type = "";
  query.start = "";
  query.end = "";
  load();
}

function onPage(p: number) {
  query.page = p;
  load();
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
