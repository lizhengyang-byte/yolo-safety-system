<template>
  <el-card>
    <template #header>
      <div class="card-head-row">
        <div class="card-head-title">
          <span class="ico"><el-icon><Warning /></el-icon></span>
          违规抓拍记录
          <small class="head-hint">点击行查看详情</small>
        </div>
        <el-button type="primary" @click="load">
          <el-icon class="btn-ico"><Refresh /></el-icon>刷新
        </el-button>
      </div>
    </template>

    <!-- 筛选 -->
    <el-form inline class="filter-bar">
      <el-form-item label="违规类型">
        <el-select v-model="query.violation_type" clearable placeholder="全部" style="width: 160px">
          <el-option
            v-for="opt in VIOLATION_TYPE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="摄像头">
        <el-select v-model="query.camera_id" clearable placeholder="全部" style="width: 160px">
          <el-option
            v-for="c in cameras"
            :key="c.id"
            :label="`${c.name}${c.location ? '（' + c.location + '）' : ''}`"
            :value="c.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="query.start" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="query.end" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table
      :data="items"
      border
      stripe
      v-loading="loading"
      @row-click="openDetail"
      style="cursor: pointer"
    >
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

    <!-- 违规详情抽屉 -->
    <el-drawer v-model="drawerVisible" size="560px" :title="detailTitle">
      <div v-if="detail" v-loading="false">
        <el-radio-group v-model="viewMode" style="margin-bottom: 12px">
          <el-radio-button value="anno">标注证据图</el-radio-button>
          <el-radio-button value="raw">原始帧</el-radio-button>
        </el-radio-group>
        <el-image
          :src="viewMode === 'anno' && detail.anno_url ? detail.anno_url : detail.image_url"
          fit="contain"
          style="width: 100%; max-height: 320px; border-radius: 6px; background: #000"
          :preview-src-list="detail.anno_url ? [detail.anno_url, detail.image_url] : [detail.image_url]"
          preview-teleported
        />

        <el-descriptions :column="2" border style="margin-top: 16px">
          <el-descriptions-item label="摄像头">{{ detail.camera_name || "未命名" }}</el-descriptions-item>
          <el-descriptions-item label="违规类型">
            <el-tag :type="tagType(detail.violation_type)">
              {{ VIOLATION_TYPE_MAP[detail.violation_type] || detail.violation_type }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ (detail.confidence * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="抓拍时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 20px 0 8px">该帧检测目标（AI 识别明细）</h4>
        <el-table v-if="detail.detections?.length" :data="detail.detections" size="small" border>
          <el-table-column label="目标" width="180">
            <template #default="{ row }">
              <el-tag size="small" :style="{ background: classColor(row.cls_name), borderColor: classColor(row.cls_name), color: '#fff' }">
                {{ row.cls_name }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="110">
            <template #default="{ row }"> {{ (row.conf * 100).toFixed(1) }}% </template>
          </el-table-column>
          <el-table-column label="区域 (x1,y1,x2,y2)">
            <template #default="{ row }">
              {{ row.box.map((n: number) => Math.round(n)).join(", ") }}
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="该记录无检测明细（旧数据或元数据上报）" :image-size="60" />
      </div>
    </el-drawer>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { listCameras, type Camera } from "@/api/camera";
import { listViolations, type Violation } from "@/api/violation";
import {
  VIOLATION_TYPE_MAP,
  VIOLATION_TYPE_OPTIONS,
  classColor,
} from "@/constants/violations";

const items = ref<Violation[]>([]);
const total = ref(0);
const loading = ref(false);
const cameras = ref<Camera[]>([]);
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
const viewMode = ref<"anno" | "raw">("anno");

const detailTitle = computed(() => {
  if (!detail.value) return "违规详情";
  const type = VIOLATION_TYPE_MAP[detail.value.violation_type] || detail.value.violation_type;
  return `违规 #${detail.value.id} · ${type}`;
});

function tagType(type: string) {
  if (type === "no_helmet" || type === "fire" || type === "zone_intrusion") return "danger";
  if (type === "no_vest" || type === "smoke") return "warning";
  return "info";
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

function reset() {
  query.page = 1;
  query.violation_type = "";
  query.camera_id = undefined;
  query.start = "";
  query.end = "";
  load();
}

function onPage(p: number) {
  query.page = p;
  load();
}

function openDetail(row: Violation) {
  detail.value = row;
  viewMode.value = row.anno_url ? "anno" : "raw";
  drawerVisible.value = true;
}

onMounted(async () => {
  load();
  try {
    cameras.value = await listCameras();
  } catch {
    /* 摄像头列表拉取失败不影响列表加载 */
  }
});
</script>

<style scoped>
.filter-bar :deep(.el-form-item:last-child) {
  margin-bottom: 14px;
}
</style>
