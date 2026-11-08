<template>
  <div class="login-page">
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>
    <div class="bg-grid"></div>

    <div class="login-wrap">
      <!-- 品牌介绍 -->
      <section class="brand-panel">
        <div class="brand-badge">
          <span class="brand-badge-mark"><el-icon><Aim /></el-icon></span>
          <span>智慧工地</span>
        </div>
        <h1 class="brand-h1">AI 安全智能监测平台</h1>
        <p class="brand-p">
          YOLO 实时识别 · 违规自动抓拍留痕 · 安全台账一键导出
        </p>
        <ul class="feature-list">
          <li>
            <span class="feat-ico"><el-icon><VideoCamera /></el-icon></span>
            <div>
              <b>多路 RTSP 实时监控</b>
              <small>AI 检测框实时叠加，违规即时告警</small>
            </div>
          </li>
          <li>
            <span class="feat-ico"><el-icon><Warning /></el-icon></span>
            <div>
              <b>危险行为智能识别</b>
              <small>未戴安全帽 / 反光马甲 / 口罩</small>
            </div>
          </li>
          <li>
            <span class="feat-ico"><el-icon><DataAnalysis /></el-icon></span>
            <div>
              <b>数据看板与安全报告</b>
              <small>趋势洞察 · 周报 / 月报 PDF 导出</small>
            </div>
          </li>
        </ul>
      </section>

      <!-- 登录卡片 -->
      <el-card class="login-card">
        <div class="card-head">
          <h2>欢迎登录</h2>
          <p>请使用管理员账号进入安全监测系统</p>
        </div>
        <el-form @keyup.enter="onLogin">
          <el-form-item>
            <el-input
              v-model="form.username"
              size="large"
              placeholder="用户名"
              :prefix-icon="User"
            />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <div class="row-between">
            <el-checkbox v-model="remember">记住密码</el-checkbox>
          </div>
          <el-button
            class="login-btn"
            type="primary"
            size="large"
            :loading="loading"
            @click="onLogin"
          >
            登 录
          </el-button>
        </el-form>
        <div class="tip">默认账号：admin / admin123</div>
      </el-card>
    </div>

    <div class="copyright">© 2026 智慧工地 AI 安全监测平台 · All Rights Reserved</div>
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
  position: relative;
  height: 100vh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(1200px 700px at 78% 18%, #123b73 0%, transparent 55%),
    radial-gradient(1000px 600px at 10% 90%, #0a2a4d 0%, transparent 55%),
    linear-gradient(135deg, #060b16 0%, #0b1730 50%, #071021 100%);
}

/* 背景光晕 */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.55;
  pointer-events: none;
}
.orb-1 {
  width: 520px;
  height: 520px;
  top: -160px;
  right: -80px;
  background: radial-gradient(circle, rgba(47, 107, 255, 0.65), transparent 70%);
}
.orb-2 {
  width: 460px;
  height: 460px;
  bottom: -180px;
  left: -120px;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.45), transparent 70%);
}
.orb-3 {
  width: 300px;
  height: 300px;
  top: 40%;
  left: 46%;
  background: radial-gradient(circle, rgba(124, 184, 255, 0.28), transparent 70%);
}
.bg-grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: radial-gradient(circle at 50% 45%, #000 0%, transparent 78%);
  -webkit-mask-image: radial-gradient(circle at 50% 45%, #000 0%, transparent 78%);
  pointer-events: none;
}

.login-wrap {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: stretch;
  gap: 44px;
  width: 100%;
  max-width: 1020px;
  padding: 0 32px;
}

/* 品牌区 */
.brand-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: #fff;
  animation: riseIn 0.6s var(--ease-out) both;
}
.brand-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 7px 14px 7px 8px;
  width: fit-content;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #dbe7ff;
  font-size: 13px;
  letter-spacing: 1px;
  backdrop-filter: blur(8px);
}
.brand-badge-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--brand-500), var(--cyan-400));
  font-size: 16px;
}
.brand-h1 {
  margin-top: 24px;
  font-size: 40px;
  line-height: 1.18;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(120deg, #ffffff 20%, #9cc4ff 70%, #67e8f9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.brand-p {
  margin-top: 14px;
  color: #9db1cd;
  font-size: 15px;
  letter-spacing: 0.4px;
}
.feature-list {
  list-style: none;
  margin-top: 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.feature-list li {
  display: flex;
  align-items: center;
  gap: 14px;
}
.feat-ico {
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #9cc4ff;
  background: rgba(47, 107, 255, 0.16);
  border: 1px solid rgba(79, 156, 255, 0.3);
}
.feature-list b {
  display: block;
  font-size: 15px;
  color: #e8f0ff;
  font-weight: 600;
}
.feature-list small {
  color: #8ba0bd;
  font-size: 12.5px;
}

/* 登录卡片 */
.login-card {
  flex: 0 0 400px;
  width: 400px;
  align-self: center;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 30px 80px rgba(2, 8, 20, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(18px);
  animation: riseIn 0.7s var(--ease-out) both;
}
.login-card :deep(.el-card__body) {
  padding: 38px 34px 30px;
}
.card-head {
  margin-bottom: 26px;
}
.card-head h2 {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-1);
  letter-spacing: 1px;
}
.card-head p {
  margin-top: 8px;
  color: var(--text-3);
  font-size: 13.5px;
}
.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.login-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  letter-spacing: 6px;
  border-radius: 12px;
}
.tip {
  margin-top: 22px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-3);
}

.copyright {
  position: absolute;
  bottom: 22px;
  left: 0;
  right: 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.34);
  font-size: 12px;
  letter-spacing: 0.5px;
  z-index: 2;
}

@media (max-width: 880px) {
  .login-wrap {
    flex-direction: column;
    max-width: 440px;
    gap: 26px;
  }
  .brand-panel {
    text-align: center;
    align-items: center;
  }
  .brand-h1 {
    font-size: 30px;
  }
  .feature-list {
    display: none;
  }
  .login-card {
    flex: none;
    width: 100%;
  }
  .copyright {
    display: none;
  }
}
</style>
