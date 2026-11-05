<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">工地AI安全智能监测系统</h2>
      <el-form @keyup.enter="onLogin">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名（默认 admin）"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（默认 admin123）"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" :loading="loading" @click="onLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";
import { login } from "@/api/auth";

const router = useRouter();
const loading = ref(false);
const form = reactive({ username: "admin", password: "admin123" });

async function onLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const res = await login(form);
    localStorage.setItem("token", res.access_token);
    router.push("/dashboard");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f3b73 0%, #2f6fb3 100%);
}
.login-card {
  width: 400px;
  padding: 20px 10px;
}
.title {
  text-align: center;
  margin-bottom: 24px;
  color: #333;
}
</style>
