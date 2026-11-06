<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">工地AI安全智能监测系统</h2>
      <el-form @keyup.enter="onLogin">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="remember">记住密码</el-checkbox>
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
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";
import { login } from "@/api/auth";

const router = useRouter();
const loading = ref(false);
const remember = ref(false);
const form = reactive({ username: "", password: "" });

// 记住密码：本地保存账号，下次自动填好
const REMEMBER_KEY = "yolo_remembered";

onMounted(() => {
  try {
    const saved = localStorage.getItem(REMEMBER_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.username) {
        form.username = parsed.username;
        form.password = parsed.password || "";
        remember.value = true;
      }
    }
  } catch {
    /* 数据损坏则忽略 */
  }
});

async function onLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const res = await login(form);
    localStorage.setItem("token", res.access_token);
    if (remember.value) {
      localStorage.setItem(
        REMEMBER_KEY,
        JSON.stringify({ username: form.username, password: form.password })
      );
    } else {
      localStorage.removeItem(REMEMBER_KEY);
    }
    router.push("/dashboard");
  } catch (e) {
    // 后端 detail 已由拦截器统一提示（如"用户名或密码错误"）
    console.warn("登录失败", e);
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
