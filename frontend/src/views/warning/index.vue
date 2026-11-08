<template>
  <div>
    <!-- 预警规则管理 -->
    <el-card>
      <template #header>
        <div class="card-head-row">
          <div class="card-head-title">
            <span class="ico"><el-icon><Bell /></el-icon></span>
            预警规则
            <el-tooltip
              content="规则生效后，某摄像头（或全部）在时间窗口内违规次数达到阈值，即自动生成预警事件并在顶栏铃铛提醒"
              placement="top"
            >
              <el-icon class="hint-ico"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          <el-button type="primary" @click="openCreate">
            <el-icon class="btn-ico"><Plus /></el-icon>新增规则
          </el-button>
        </div>
      </template>

      <el-table :data="rules" border stripe v-loading="ruleLoading">
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column label="摄像头" width="150">
          <template #default="{ row }">
            {{ row.camera_id ? cameraName(row.camera_id) : "全部摄像头" }}
          </template>
        </el-table-column>
        <el-table-column label="违规类型" width="140">
          <template #default="{ row }">
            {{ row.violation_type ? (VIOLATION_TYPE_MAP[row.violation_type] || row.violation_type) : "全部类型" }}
          </template>
        </el-table-column>
        <el-table-column label="触发条件" min-width="150">
          <template #default="{ row }">
            {{ row.window_minutes }} 分钟内 ≥ {{ row.threshold }} 次
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">
              {{ row.enabled ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              style="margin-right: 12px"
              @change="toggleRule(row)"
            />
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="onDeleteRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 规则编辑对话框 -->
      <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="480px">
        <el-form :model="form" label-width="100px">
          <el-form-item label="规则名称" required>
            <el-input v-model="form.name" placeholder="如：东门违规频发预警" />
          </el-form-item>
          <el-form-item label="摄像头">
            <el-select v-model="form.camera_id" clearable placeholder="全部摄像头" style="width: 100%">
              <el-option v-for="c in cameras" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="违规类型">
            <el-select v-model="form.violation_type" clearable placeholder="全部类型" style="width: 100%">
              <el-option v-for="opt in VIOLATION_TYPE_OPTIONS" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="触发条件">
            <div class="cond-row">
              <el-input-number v-model="form.window_minutes" :min="1" :max="1440" style="width: 130px" />
              <span class="cond-text">分钟内违规 ≥</span>
              <el-input-number v-model="form.threshold" :min="1" :max="10000" style="width: 120px" />
              <span class="cond-text">次</span>
            </div>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.enabled" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="onSaveRule">保存</el-button>
        </template>
      </el-dialog>
    </el-card>

    <!-- 预警事件 -->
    <el-card style="margin-top: 16px">
      <template #header>
        <div class="card-head-row">
          <div class="card-head-title">
            <span class="ico"><el-icon><BellFilled /></el-icon></span>
            预警事件
          </div>
          <div class="event-actions">
            <el-radio-group v-model="unreadOnly" @change="loadEvents">
              <el-radio-button :label="false">全部</el-radio-button>
              <el-radio-button :label="true">仅未读</el-radio-button>
            </el-radio-group>
            <el-button :disabled="!selectedIds.length" @click="markSelectedRead">
              <el-icon class="btn-ico"><Check /></el-icon>标记已读
            </el-button>
            <el-button @click="markAllReadFn">
              <el-icon class="btn-ico"><Select /></el-icon>全部已读
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="events"
        border stripe
        v-loading="eventLoading"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column prop="triggered_at" label="触发时间" width="180" />
        <el-table-column prop="camera_name" label="摄像头" min-width="120" />
        <el-table-column label="违规类型" width="140">
          <template #default="{ row }">
            <el-tag :type="tagType(row.violation_type)">
              {{ VIOLATION_TYPE_MAP[row.violation_type] || row.violation_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="窗口内次数" width="110">
          <template #default="{ row }">
            <b style="color: #f56c6c">{{ row.count }}</b> 次
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'danger'" effect="plain">
              {{ row.is_read ? "已读" : "未读" }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        style="margin-top: 16px; justify-content: flex-end"
        layout="total, prev, pager, next"
        :total="eventTotal"
        :page-size="eventQuery.page_size"
        :current-page="eventQuery.page"
        @current-change="(p: number) => { eventQuery.page = p; loadEvents(); }"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { QuestionFilled } from "@element-plus/icons-vue";
import { listCameras, type Camera } from "@/api/camera";
import {
  createRule,
  deleteRule,
  listEvents,
  listRules,
  markAllRead,
  markRead,
  updateRule,
  type WarningEvent,
  type WarningRule,
} from "@/api/warning";
import { VIOLATION_TYPE_MAP, VIOLATION_TYPE_OPTIONS } from "@/constants/violations";

const rules = ref<WarningRule[]>([]);
const ruleLoading = ref(false);
const cameras = ref<Camera[]>([]);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const form = reactive({
  name: "",
  camera_id: undefined as number | undefined,
  violation_type: undefined as string | undefined,
  threshold: 3,
  window_minutes: 60,
  enabled: true,
});

const events = ref<WarningEvent[]>([]);
const eventTotal = ref(0);
const eventLoading = ref(false);
const unreadOnly = ref(false);
const selectedIds = ref<number[]>([]);
const eventQuery = reactive({ page: 1, page_size: 20 });

function onSelectionChange(rows: WarningEvent[]) {
  selectedIds.value = rows.map((r) => r.id);
}

function cameraName(id: number) {
  return cameras.value.find((c) => c.id === id)?.name || `摄像头 #${id}`;
}

function tagType(type: string) {
  if (type === "no_helmet") return "danger";
  if (type === "no_vest") return "warning";
  return "info";
}

async function loadRules() {
  ruleLoading.value = true;
  try {
    rules.value = await listRules();
  } finally {
    ruleLoading.value = false;
  }
}

async function loadEvents() {
  eventLoading.value = true;
  try {
    const res = await listEvents({
      page: eventQuery.page,
      page_size: eventQuery.page_size,
      unread_only: unreadOnly.value,
    });
    events.value = res.items;
    eventTotal.value = res.total;
  } finally {
    eventLoading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, {
    name: "",
    camera_id: undefined,
    violation_type: undefined,
    threshold: 3,
    window_minutes: 60,
    enabled: true,
  });
  dialogVisible.value = true;
}

function openEdit(row: WarningRule) {
  editingId.value = row.id;
  Object.assign(form, {
    name: row.name,
    camera_id: row.camera_id ?? undefined,
    violation_type: row.violation_type ?? undefined,
    threshold: row.threshold,
    window_minutes: row.window_minutes,
    enabled: row.enabled,
  });
  dialogVisible.value = true;
}

async function onSaveRule() {
  if (!form.name) {
    ElMessage.warning("请填写规则名称");
    return;
  }
  const payload = {
    name: form.name,
    camera_id: form.camera_id ?? null,
    violation_type: form.violation_type ?? null,
    threshold: form.threshold,
    window_minutes: form.window_minutes,
    enabled: form.enabled,
  };
  if (editingId.value) {
    await updateRule(editingId.value, payload);
  } else {
    await createRule(payload);
  }
  ElMessage.success("保存成功");
  dialogVisible.value = false;
  loadRules();
}

async function toggleRule(row: WarningRule) {
  await updateRule(row.id, { enabled: row.enabled });
  ElMessage.success(row.enabled ? "规则已启用" : "规则已停用");
}

async function onDeleteRule(row: WarningRule) {
  await ElMessageBox.confirm(`确认删除规则「${row.name}」？`, "提示", { type: "warning" });
  await deleteRule(row.id);
  ElMessage.success("删除成功");
  loadRules();
}

async function markSelectedRead() {
  if (!selectedIds.value.length) return;
  await markRead(selectedIds.value);
  ElMessage.success("已标记为已读");
  loadEvents();
}

async function markAllReadFn() {
  await markAllRead();
  ElMessage.success("已全部标记为已读");
  loadEvents();
}

onMounted(() => {
  loadRules();
  loadEvents();
  listCameras()
    .then((cams) => (cameras.value = cams))
    .catch(() => {});
});
</script>

<style scoped>
.hint-ico {
  color: var(--text-3);
  cursor: help;
}
.event-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.cond-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cond-text {
  color: #666;
  font-size: 13px;
  white-space: nowrap;
}
</style>
