<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">工地AI安全监测</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/monitor">
          <el-icon><VideoCamera /></el-icon>
          <span>实时监控</span>
        </el-menu-item>
        <el-menu-item index="/demo">
          <el-icon><Camera /></el-icon>
          <span>临时演示</span>
        </el-menu-item>
        <el-menu-item index="/camera">
          <el-icon><Monitor /></el-icon>
          <span>摄像头管理</span>
        </el-menu-item>
        <el-menu-item index="/violation">
          <el-icon><Warning /></el-icon>
          <span>违规记录</span>
        </el-menu-item>
        <el-menu-item index="/warning">
          <el-icon><Bell /></el-icon>
          <span>预警中心</span>
        </el-menu-item>
        <el-menu-item index="/log">
          <el-icon><Document /></el-icon>
          <span>安全日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title }}</span>
        <div class="header-right">
          <!-- 预警铃铛：未读数徽标 + 新增预警实时提醒 -->
          <el-badge :value="unread" :hidden="unread === 0" class="bell">
            <el-button circle @click="router.push('/warning')">
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-dropdown @command="handleCommand">
            <span class="user">
              <el-icon><User /></el-icon> admin
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElNotification } from "element-plus";
import { getUnreadCount } from "@/api/warning";

const router = useRouter();
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

onMounted(() => {
  pollUnread();
  bellTimer = window.setInterval(pollUnread, 10000);
});

onBeforeUnmount(() => {
  if (bellTimer) window.clearInterval(bellTimer);
});
</script>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background: #001529;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  background: #002140;
}
.header {
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.bell {
  display: flex;
  align-items: center;
}
.user {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #333;
}
.main {
  background: #f0f2f5;
}
.el-menu {
  border-right: none;
}
</style>
