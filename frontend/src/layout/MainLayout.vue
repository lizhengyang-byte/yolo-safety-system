<template>
  <div class="app-shell" :class="{ 'is-collapsed': collapsed }">
    <!-- 侧栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">
          <el-icon><Aim /></el-icon>
        </div>
        <transition name="fade">
          <div v-show="!collapsed" class="brand-text">
            <span class="brand-title">智慧工地</span>
            <span class="brand-sub">AI 安全监测平台</span>
          </div>
        </transition>
      </div>

      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="$route.path"
          router
          :collapse="collapsed"
          :collapse-transition="false"
          class="side-menu"
          background-color="transparent"
          text-color="#a9b8d0"
          active-text-color="#ffffff"
        >
          <div v-show="!collapsed" class="menu-group">总览</div>
          <el-menu-item index="/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>数据看板</template>
          </el-menu-item>

          <div v-show="!collapsed" class="menu-group">监控中心</div>
          <el-menu-item index="/monitor">
            <el-icon><VideoCamera /></el-icon>
            <template #title>实时监控</template>
          </el-menu-item>
          <el-menu-item index="/demo">
            <el-icon><Camera /></el-icon>
            <template #title>临时演示</template>
          </el-menu-item>

          <div v-show="!collapsed" class="menu-group">安全管理</div>
          <el-menu-item index="/camera">
            <el-icon><Monitor /></el-icon>
            <template #title>摄像头管理</template>
          </el-menu-item>
          <el-menu-item index="/violation">
            <el-icon><Warning /></el-icon>
            <template #title>违规记录</template>
          </el-menu-item>
          <el-menu-item index="/warning">
            <el-icon><Bell /></el-icon>
            <template #title>预警中心</template>
          </el-menu-item>
          <el-menu-item index="/log">
            <el-icon><Document /></el-icon>
            <template #title>安全日志</template>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>

      <div v-show="!collapsed" class="sidebar-foot">
        <span class="pulse-dot"></span>
        <span>系统运行中</span>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-shell">
      <header class="topbar">
        <div class="topbar-left">
          <button
            class="icon-btn"
            :title="collapsed ? '展开菜单' : '收起菜单'"
            @click="collapsed = !collapsed"
          >
            <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </button>
          <div class="page-head">
            <span class="page-title">{{ $route.meta.title }}</span>
            <span class="page-crumb">首页 / {{ $route.meta.title }}</span>
          </div>
        </div>

        <div class="topbar-right">
          <button class="icon-btn" title="进入智慧大屏" @click="router.push('/screen')">
            <el-icon><DataBoard /></el-icon>
          </button>
          <el-badge :value="unread" :hidden="unread === 0" class="bell">
            <button class="icon-btn bell-btn" title="预警提醒" @click="router.push('/warning')">
              <el-icon><Bell /></el-icon>
            </button>
          </el-badge>
          <span class="top-divider"></span>
          <el-dropdown @command="handleCommand">
            <span class="user">
              <span class="avatar">A</span>
              <span class="user-meta">
                <span class="user-name">admin</span>
                <span class="user-role">系统管理员</span>
              </span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElNotification } from "element-plus";
import { getUnreadCount } from "@/api/warning";
import { useRealtime } from "@/composables/useRealtime";

const router = useRouter();
const collapsed = ref(false);
const unread = ref(0);
let lastUnread = 0;
let bellTimer: number | null = null;

/** 轮询未读预警数：增加时顶栏弹红色预警通知 */
async function pollUnread() {
  try {
    const { count } = await getUnreadCount();
    unread.value = count;
    if (count > 0 && count !== lastUnread) {
      ElNotification({
        title: "预警提醒",
        message: `当前有 ${count} 条未读预警事件，点击铃铛查看`,
        type: "warning",
        duration: 6000,
      });
    }
    lastUnread = count;
  } catch {
    /* 后端暂不可用则跳过 */
  }
}

function handleCommand(cmd: string) {
  if (cmd === "logout") {
    localStorage.removeItem("token");
    router.push("/login");
  }
}

// 实时推送：新预警到达立即刷新铃铛（SSE），60s 轮询仅作兜底
useRealtime({
  warning: () => pollUnread(),
});

onMounted(() => {
  pollUnread();
  bellTimer = window.setInterval(pollUnread, 60000);
});

onBeforeUnmount(() => {
  if (bellTimer) window.clearInterval(bellTimer);
});
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-app);
}

/* ================= 侧栏 ================= */
.sidebar {
  position: relative;
  flex: 0 0 var(--aside-w);
  width: var(--aside-w);
  display: flex;
  flex-direction: column;
  background: radial-gradient(120% 80% at 0% 0%, var(--sidebar-3) 0%, var(--sidebar-2) 45%, var(--sidebar-1) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: flex-basis var(--dur) var(--ease), width var(--dur) var(--ease);
  overflow: hidden;
  z-index: 20;
}
.sidebar::after {
  content: "";
  position: absolute;
  top: -60px;
  left: -60px;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(47, 107, 255, 0.4), transparent 68%);
  filter: blur(6px);
  pointer-events: none;
}
.is-collapsed .sidebar {
  flex-basis: var(--aside-w-collapsed);
  width: var(--aside-w-collapsed);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: var(--header-h);
  padding: 0 20px;
  border-bottom: 1px solid var(--sidebar-line);
  flex-shrink: 0;
}
.brand-mark {
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #fff;
  background: linear-gradient(135deg, var(--brand-500), var(--cyan-400));
  box-shadow: 0 8px 18px rgba(47, 107, 255, 0.45);
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  white-space: nowrap;
}
.brand-title {
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
}
.brand-sub {
  color: var(--sidebar-text-dim);
  font-size: 11px;
  letter-spacing: 2px;
}

.menu-scroll {
  flex: 1;
  padding: 12px 12px 8px;
}
.menu-group {
  padding: 14px 14px 8px;
  color: var(--sidebar-text-dim);
  font-size: 11px;
  letter-spacing: 2px;
  font-weight: 600;
  text-transform: uppercase;
}

/* 菜单项皮肤 */
.side-menu {
  border-right: none !important;
  background: transparent !important;
}
.side-menu :deep(.el-menu-item) {
  height: 46px;
  line-height: 46px;
  margin: 4px 0;
  border-radius: 11px;
  font-size: 14px;
  color: var(--sidebar-text);
  transition: all var(--dur-fast) var(--ease);
}
.side-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
  color: var(--sidebar-text-dim);
  transition: color var(--dur-fast) var(--ease);
}
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.side-menu :deep(.el-menu-item:hover .el-icon) {
  color: #fff;
}
.side-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: linear-gradient(90deg, rgba(47, 107, 255, 0.4), rgba(47, 107, 255, 0.08));
  box-shadow: inset 0 0 0 1px rgba(79, 156, 255, 0.28);
  position: relative;
}
.side-menu :deep(.el-menu-item.is-active)::before {
  content: "";
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 22px;
  border-radius: 0 4px 4px 0;
  background: linear-gradient(180deg, var(--brand-400), var(--cyan-400));
  box-shadow: 0 0 12px rgba(79, 156, 255, 0.9);
}
.side-menu :deep(.el-menu-item.is-active .el-icon) {
  color: #fff;
}
.side-menu :deep(.el-menu--collapse) {
  width: 100%;
}
.is-collapsed .side-menu :deep(.el-menu-item) {
  justify-content: center;
  padding: 0 !important;
}
.is-collapsed .side-menu :deep(.el-menu-item .el-icon) {
  margin: 0;
}

.sidebar-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 16px 16px;
  padding: 10px 14px;
  border-radius: 11px;
  color: var(--sidebar-text);
  font-size: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--sidebar-line);
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  animation: pulseDot 2s infinite;
}
@keyframes pulseDot {
  0% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.55);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(34, 197, 94, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
  }
}

/* ================= 主区域 ================= */
.main-shell {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  height: var(--header-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid var(--border);
  z-index: 10;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.icon-btn {
  width: 38px;
  height: 38px;
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-2);
  font-size: 17px;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}
.icon-btn:hover {
  color: var(--brand-500);
  border-color: var(--brand-300);
  background: var(--el-color-primary-light-9);
  transform: translateY(-1px);
}
.page-head {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
  letter-spacing: 0.3px;
}
.page-crumb {
  font-size: 12px;
  color: var(--text-3);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.bell {
  display: flex;
  align-items: center;
}
.bell-btn {
  font-size: 18px;
}
.top-divider {
  width: 1px;
  height: 26px;
  background: var(--border);
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 12px;
  transition: background var(--dur-fast) var(--ease);
}
.user:hover {
  background: var(--surface-muted);
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 15px;
  background: linear-gradient(135deg, var(--brand-500), var(--cyan-400));
  box-shadow: 0 6px 14px rgba(47, 107, 255, 0.3);
}
.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.user-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-1);
}
.user-role {
  font-size: 11px;
  color: var(--text-3);
}
.caret {
  color: var(--text-3);
  font-size: 13px;
}

.content {
  flex: 1;
  overflow: auto;
  padding: 22px 24px 28px;
  background:
    radial-gradient(900px 420px at 100% -10%, rgba(47, 107, 255, 0.06), transparent 60%),
    radial-gradient(700px 380px at -10% 0%, rgba(34, 211, 238, 0.05), transparent 55%),
    var(--bg-app);
}

/* 折叠时隐藏用户文字 */
.is-collapsed .user-meta,
.is-collapsed .caret {
  display: none;
}

@media (max-width: 860px) {
  .page-crumb {
    display: none;
  }
  .user-meta {
    display: none;
  }
  .content {
    padding: 16px 14px 22px;
  }
}
</style>
