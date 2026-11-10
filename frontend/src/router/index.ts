import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
  },
  {
    // 智慧大屏：独立全屏路由（不套后台 MainLayout，无侧栏/顶栏）
    path: "/screen",
    name: "Screen",
    component: () => import("@/views/screen/index.vue"),
    meta: { title: "智慧大屏" },
  },
  {
    path: "/",
    component: () => import("@/layout/MainLayout.vue"),
    redirect: "/dashboard",
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/Dashboard.vue"),
        meta: { title: "数据看板" },
      },
      {
        path: "monitor",
        name: "Monitor",
        component: () => import("@/views/monitor/index.vue"),
        meta: { title: "实时监控" },
      },
      {
        path: "demo",
        name: "Demo",
        component: () => import("@/views/demo/index.vue"),
        meta: { title: "临时演示" },
      },
      {
        path: "camera",
        name: "Camera",
        component: () => import("@/views/camera/index.vue"),
        meta: { title: "摄像头管理" },
      },
      {
        path: "zone",
        name: "Zone",
        component: () => import("@/views/zone/index.vue"),
        meta: { title: "危险区域" },
      },
      {
        path: "violation",
        name: "Violation",
        component: () => import("@/views/violation/index.vue"),
        meta: { title: "违规记录" },
      },
      {
        path: "warning",
        name: "Warning",
        component: () => import("@/views/warning/index.vue"),
        meta: { title: "预警中心" },
      },
      {
        path: "log",
        name: "Log",
        component: () => import("@/views/log/index.vue"),
        meta: { title: "安全日志" },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 简单路由守卫：未登录跳转登录页
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem("token");
  if (to.name !== "Login" && !token) {
    next({ name: "Login" });
  } else {
    next();
  }
});

export default router;
