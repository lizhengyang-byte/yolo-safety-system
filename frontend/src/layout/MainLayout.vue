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
        <el-menu-item index="/log">
          <el-icon><Document /></el-icon>
          <span>安全日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title }}</span>
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
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function handleCommand(cmd: string) {
  if (cmd === "logout") {
    localStorage.removeItem("token");
    router.push("/login");
  }
}
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
