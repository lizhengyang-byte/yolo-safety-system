<template>
  <el-card>
    <template #header>
      <div class="header">
        <span>摄像头设备管理</span>
        <el-button type="primary" @click="openCreate">新增摄像头</el-button>
      </div>
    </template>

    <el-table :data="cameras" border stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="location" label="点位" />
      <el-table-column prop="rtsp_url" label="RTSP地址" show-overflow-tooltip />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'online' ? 'success' : 'info'">
            {{ row.status === "online" ? "在线" : "离线" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" @change="toggleEnabled(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑摄像头' : '新增摄像头'" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：东门一号" />
        </el-form-item>
        <el-form-item label="安装点位">
          <el-input v-model="form.location" placeholder="如：3号塔吊下方" />
        </el-form-item>
        <el-form-item label="RTSP地址" required>
          <el-input v-model="form.rtsp_url" placeholder="rtsp://user:pass@ip:554/stream1" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { listCameras, createCamera, updateCamera, deleteCamera, type Camera } from "@/api/camera";

const cameras = ref<Camera[]>([]);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const form = reactive({
  name: "",
  location: "",
  rtsp_url: "",
  enabled: true,
});

async function load() {
  cameras.value = await listCameras();
}

function openCreate() {
  editingId.value = null;
  Object.assign(form, { name: "", location: "", rtsp_url: "", enabled: true });
  dialogVisible.value = true;
}

function openEdit(row: Camera) {
  editingId.value = row.id;
  Object.assign(form, {
    name: row.name,
    location: row.location,
    rtsp_url: row.rtsp_url,
    enabled: row.enabled,
  });
  dialogVisible.value = true;
}

async function onSave() {
  if (!form.name || !form.rtsp_url) {
    ElMessage.warning("请填写名称和RTSP地址");
    return;
  }
  if (editingId.value) {
    await updateCamera(editingId.value, { ...form });
  } else {
    await createCamera({ ...form });
  }
  ElMessage.success("保存成功");
  dialogVisible.value = false;
  load();
}

async function toggleEnabled(row: Camera) {
  await updateCamera(row.id, { enabled: row.enabled });
  ElMessage.success(row.enabled ? "已启用" : "已停用");
}

async function onDelete(row: Camera) {
  await ElMessageBox.confirm(`确认删除摄像头「${row.name}」？`, "提示", { type: "warning" });
  await deleteCamera(row.id);
  ElMessage.success("删除成功");
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
