<template>
  <el-card>
    <template #header>
      <div class="card-head-row">
        <div class="card-head-title">
          <span class="ico"><el-icon><Document /></el-icon></span>
          安全日志管理
        </div>
        <div class="actions">
          <el-select
            v-model="query.violation_type"
            clearable
            placeholder="违规类型"
            style="width: 140px; margin-right: 10px"
          >
            <el-option
              v-for="opt in VIOLATION_TYPE_OPTIONS"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-select
            v-model="query.camera_id"
            clearable
            placeholder="摄像头"
            style="width: 140px; margin-right: 10px"
          >
            <el-option
              v-for="c in cameras"
              :key="c.id"
              :label="c.name"
              :value="c.id"
            />
          </el-select>
          <el-date-picker
            v-model="range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="margin-right: 10px"
          />
          <el-button type="primary" :loading="exporting" @click="exportExcel">
            <el-icon class="btn-ico"><Download /></el-icon>导出 Excel（含违规图片）
          </el-button>
        </div>
      </div>
    </template>

    <el-alert
      title="违规记录自动生成安全日志，支持按类型/摄像头/时间段筛选导出为带违规图片的 Excel 安全台账（后端用 pandas + openpyxl 生成）。"
      type="success"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-table :data="items" border stripe v-loading="loading" @row-click="openDetail" style="cursor: pointer">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="camera_name" label="摄像头" />
      <el-table-column label="违规类型" width="140">
        <template #default="{ row }">
          <el-tag :type="tagType(row.violation_type)">
            {{ VIOLATION_TYPE_MAP[row.violation_type] || row.violation_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置信度" width="100">
        <template #default="{ row }"> {{ (row.confidence * 100).toFixed(1) }}% </template>
      </el-table-column>
      <el-table-column prop="created_at" label="抓拍时间" width="180" />
      <el-table-column label="标注证据图" width="110">
        <template #default="{ row }">
          <el-image
            v-if="row.anno_url || row.image_url"
            :src="row.anno_url || row.image_url"
            fit="cover"
            style="width: 80px; height: 50px; border-radius: 4px"
            @click.stop="openDetail(row)"
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

    <!-- 违规详情抽屉（与违规记录页共用查看能力） -->
    <el-drawer v-model="drawerVisible" size="560px" :title="detailTitle">
      <div v-if="detail">
        <el-image
          :src="detail.anno_url || detail.image_url"
          fit="contain"
          style="width: 100%; max-height: 320px; border-radius: 6px; background: #000"
          :preview-src-list="detail.anno_url ? [detail.anno_url, detail.image_url] : [detail.image_url]"
          preview-teleported
        />
        <el-descriptions :column="2" border style="margin-top: 16px">
          <el-descriptions-item label="摄像头">{{ detail.camera_name || "未命名" }}</el-descriptions-item>
          <el-descriptions-item label="违规类型">
            {{ VIOLATION_TYPE_MAP[detail.violation_type] || detail.violation_type }}
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ (detail.confidence * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="抓拍时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import axios from "axios";
import { ElMessage } from "element-plus";
import { listCameras, type Camera } from "@/api/camera";
import { listViolations, type Violation } from "@/api/violation";
import { VIOLATION_TYPE_MAP, VIOLATION_TYPE_OPTIONS } from "@/constants/violations";

const items = ref<Violation[]>([]);
const total = ref(0);
const loading = ref(false);
const exporting = ref(false);
const cameras = ref<Camera[]>([]);
const range = ref<[string, string] | null>(null);
const query = reactive({
  page: 1,
  page_size: 20,
  violation_type: "" as string,
  camera_id: undefined as number | undefined,
  start: "" as string,
  end: "" as string,
});

// 详情抽屉
const drawerVisible = ref(false);
const detail = ref<Violation | null>(null);
const detailTitle = computed(() => {
  if (!detail.value) return "违规详情";
  const type = VIOLATION_TYPE_MAP[detail.value.violation_type] || detail.value.violation_type;
  return `违规 #${detail.value.id} · ${type}`;
});

function tagType(type: string) {
  if (type === "no_helmet") return "danger";
  if (type === "no_vest") return "warning";
  return "info";
}

function openDetail(row: Violation) {
  detail.value = row;
  drawerVisible.value = true;
}

async function load() {
  loading.value = true;
  try {
    const res = await listViolations(query);
    items.value = res.items;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

function onPage(p: number) {
  query.page = p;
  load();
}

/** 从 Content-Disposition 解析文件名（支持 filename*=UTF-8'' 中文） */
function parseFilename(disposition: string | null): string | null {
  if (!disposition) return null;
  const star = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      /* fallthrough */
    }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : null;
}

async function exportExcel() {
  if (exporting.value) return;
  exporting.value = true;
  try {
    if (range.value && range.value.length === 2) {
      query.start = range.value[0];
      query.end = range.value[1];
    } else {
      query.start = "";
      query.end = "";
    }
    // 用原生 axios 拿 Blob + 响应头（request 拦截器会返回 data 而丢失 header）
    const resp = await axios.get("/api/logs/export", {
      params: {
        violation_type: query.violation_type || undefined,
        camera_id: query.camera_id || undefined,
        start: query.start || undefined,
        end: query.end || undefined,
      },
      responseType: "blob",
      headers: { Authorization: `Bearer ${localStorage.getItem("token") || ""}` },
      timeout: 120000,
    });
    if (resp.status !== 200) {
      throw new Error(`导出失败（HTTP ${resp.status}）`);
    }
    const blob = resp.data as Blob;
    if (blob.size < 1000 && (blob.type.includes("json") || blob.type.includes("text"))) {
      // 后端返回了错误 JSON/文本（如 500），读出来提示
      const text = await blob.text();
      throw new Error(text || "导出失败，请稍后重试");
    }
    const filename = parseFilename(resp.headers["content-disposition"]) || "safety_logs.xlsx";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    ElMessage.success(`导出成功（${(blob.size / 1024 / 1024).toFixed(1)} MB）`);
  } catch (e) {
    ElMessage.error((e as Error).message || "导出失败，请稍后重试");
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  load();
  listCameras()
    .then((cams) => (cameras.value = cams))
    .catch(() => {});
});
</script>

<style scoped>
.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
