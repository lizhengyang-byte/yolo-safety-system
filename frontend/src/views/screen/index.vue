<template>
  <div ref="rootRef" class="screen-viewport" :class="{ 'is-present': present }">
    <div class="screen-stage" :style="stageStyle">
      <ScreenHeader
        :online="data.online_cameras"
        :unread="unread"
        :is-fullscreen="isFullscreen"
        :rotate-on="rotateOn"
        @toggle-fullscreen="toggleFullscreen"
        @toggle-rotate="toggleRotate"
        @exit="exitScreen"
      />

      <transition name="banner">
        <div v-if="banner" class="alert-banner">
          <span class="ab-pulse"></span>
          <span class="ab-tag">预警</span>
          <span class="ab-type">{{ banner.typeLabel }}</span>
          <span class="ab-cam">{{ banner.camera }}</span>
          <span class="ab-time">{{ banner.time }}</span>
        </div>
      </transition>

      <div class="screen-main" :class="'layout-' + layoutMode">
        <template v-if="layoutMode === 'alerts'">
          <AlertPanel class="grow-alert" :summary="data.warning_summary" />
          <CameraStatusPanel class="grow" :cameras="data.camera_status || []" />
          <RankPanel
            class="grow"
            :ranking="data.ranking"
            :location-ranking="data.location_ranking"
          />
        </template>
        <template v-else>
          <div class="col col-left">
            <KpiPanel
              class="p-kpi"
              :today="data.today"
              :total="data.total"
              :online="data.online_cameras"
              :total-cameras="cameraTotal"
              :week-total="weekTotal"
              :days="days"
              :deltas="data.deltas"
              :avg-confidence="data.avg_confidence"
            />
            <TypePanel class="grow" :types="data.types" :days="days" />
            <RankPanel
              class="grow"
              :ranking="data.ranking"
              :location-ranking="data.location_ranking"
            />
          </div>

          <div class="col col-center">
            <TrendPanel
              class="grow-trend"
              :trend="data.trend"
              :hourly="data.hourly"
              :days="days"
              :deltas="data.deltas"
            />
            <LiveFeedPanel class="grow" :latest="data.latest || []" />
          </div>

          <div class="col col-right">
            <AlertPanel class="grow-alert" :summary="data.warning_summary" />
            <CameraStatusPanel class="grow" :cameras="data.camera_status || []" />
          </div>
        </template>
      </div>

      <footer class="screen-foot">
        <span class="sf-left">
          <span class="sf-live"></span>
          数据更新：{{ lastUpdated || "--" }}
          <span class="sf-sep">|</span>
          {{ realtimeConnected ? "实时推送已连接" : "轮询兜底（60s）" }}
        </span>
        <span class="sf-right">
          <span v-if="error" class="sf-error">● {{ error }}</span>
          <span v-else class="sf-ok">● 接口正常</span>
          <span class="sf-sep">|</span>
          YOLO 安全监测系统 v1.0
        </span>
      </footer>
    </div>

    <transition name="fade">
      <div v-if="!loaded" class="loading-mask">
        <div class="lm-ring"></div>
        <p>正在加载大屏数据…</p>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import ScreenHeader from "@/components/screen/ScreenHeader.vue";
import KpiPanel from "@/components/screen/KpiPanel.vue";
import TypePanel from "@/components/screen/TypePanel.vue";
import RankPanel from "@/components/screen/RankPanel.vue";
import TrendPanel from "@/components/screen/TrendPanel.vue";
import LiveFeedPanel from "@/components/screen/LiveFeedPanel.vue";
import AlertPanel from "@/components/screen/AlertPanel.vue";
import CameraStatusPanel from "@/components/screen/CameraStatusPanel.vue";
import { useScreenScale } from "@/composables/useScreenScale";
import { usePolling } from "@/composables/usePolling";
import { useRealtime } from "@/composables/useRealtime";
import { getDashboard, type DashboardData } from "@/api/violation";
import { VIOLATION_TYPE_MAP } from "@/constants/violations";

const router = useRouter();
const route = useRoute();
const { stageStyle } = useScreenScale(1920, 1080);

const days = ref(7);
const loaded = ref(false);
const error = ref("");
const lastUpdated = ref("");
const rootRef = ref<HTMLDivElement | null>(null);
const isFullscreen = ref(false);

// ---- 大屏布局 / 值班轮播 ----
type LayoutMode = "overview" | "alerts";
const VALID_LAYOUTS: LayoutMode[] = ["overview", "alerts"];
const layoutParam = String(route.query.layout || "");
const fixedLayout: LayoutMode | null = VALID_LAYOUTS.includes(
  layoutParam as LayoutMode
)
  ? (layoutParam as LayoutMode)
  : null;
const layoutMode = ref<LayoutMode>(fixedLayout || "overview");
const rotateSec = Math.max(0, Number(route.query.rotate || 0) || 0);
const present = route.query.present === "1";
const rotateOn = ref(false); // 值班轮播是否开启（可由 URL 或页面按钮控制）
let rotateTimer: number | null = null;
const ROTATE_ORDER: LayoutMode[] = ["overview", "alerts"];
const ROTATE_PERIOD = Math.max(8, rotateSec || 25) * 1000;

// ---- 告警插播 ----
const banner = ref<{ typeLabel: string; camera: string; time: string } | null>(null);
let bannerTimer: number | null = null;

const data = ref<DashboardData>({
  total: 0,
  today: 0,
  online_cameras: 0,
  trend: [],
  types: [],
  ranking: [],
  location_ranking: [],
  deltas: undefined,
  hourly: [],
  avg_confidence: 0,
  latest: [],
  camera_status: [],
  warning_summary: { unread: 0, today: 0, latest: [] },
});

const weekTotal = computed(() => data.value.trend.reduce((s, p) => s + p.count, 0));
const cameraTotal = computed(() => (data.value.camera_status ?? []).length);
const unread = computed(() => data.value.warning_summary?.unread ?? 0);

async function load() {
  try {
    const res = await getDashboard(days.value);
    data.value = res;
    error.value = "";
    const n = new Date();
    const p = (x: number) => String(x).padStart(2, "0");
    lastUpdated.value = `${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`;
  } catch (e) {
    error.value = (e as Error)?.message || "数据加载失败";
  } finally {
    loaded.value = true;
  }
}

// 兜底轮询（正常由 SSE 实时触发）；60s 一次
usePolling(load, 60000);

// 实时推送：新违规/预警/摄像头状态立即刷新大屏
const { connected: realtimeConnected } = useRealtime({
  violation: () => load(),
  warning: (d: any) => {
    showBanner(d);
    load();
  },
  camera_status: () => load(),
});

function showBanner(d: any) {
  const typeLabel =
    d?.type_label || VIOLATION_TYPE_MAP[d?.violation_type] || d?.violation_type || "预警";
  const time = (d?.triggered_at || "").slice(11, 19) || new Date().toLocaleTimeString("zh-CN", { hour12: false });
  banner.value = { typeLabel, camera: d?.camera_name || "", time };
  if (bannerTimer !== null) window.clearTimeout(bannerTimer);
  bannerTimer = window.setTimeout(() => {
    banner.value = null;
  }, 7000);
  playBeep();
}

let audioCtx: AudioContext | null = null;
function playBeep() {
  try {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext;
    if (!Ctx) return;
    audioCtx = audioCtx || new Ctx();
    const ctx = audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.55);
    osc.start();
    osc.stop(ctx.currentTime + 0.6);
  } catch {
    /* 浏览器可能拦截自动播放，忽略 */
  }
}

function stopRotate() {
  rotateOn.value = false;
  if (rotateTimer !== null) {
    window.clearInterval(rotateTimer);
    rotateTimer = null;
  }
}

function startRotate() {
  if (rotateTimer !== null) return;
  rotateOn.value = true;
  rotateTimer = window.setInterval(() => {
    const i = ROTATE_ORDER.indexOf(layoutMode.value);
    layoutMode.value = ROTATE_ORDER[(i + 1) % ROTATE_ORDER.length];
  }, ROTATE_PERIOD);
}

/** 页面按钮：一键启停值班轮播（无需 Kiosk，直接在网页里切换布局） */
function toggleRotate() {
  if (rotateOn.value) stopRotate();
  else startRotate();
}

async function toggleFullscreen() {
  try {
    if (!document.fullscreenElement) {
      await rootRef.value?.requestFullscreen();
    } else {
      await document.exitFullscreen();
    }
  } catch {
    /* 浏览器拒绝时忽略 */
  }
}

function onFsChange() {
  isFullscreen.value = !!document.fullscreenElement;
}

function exitScreen() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  router.push("/dashboard");
}

onMounted(() => {
  document.addEventListener("fullscreenchange", onFsChange);
  // 未指定固定布局且 URL 带 rotate 时，自动进入值班轮播（等同于网页按钮「值班轮播」）
  if (!fixedLayout && rotateSec > 0) {
    startRotate();
  }
});

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", onFsChange);
  stopRotate();
  if (bannerTimer !== null) window.clearTimeout(bannerTimer);
  audioCtx?.close().catch(() => {});
});
</script>

<style scoped>
.screen-viewport {
  position: fixed;
  inset: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(1200px 600px at 50% -10%, rgba(47, 107, 255, 0.16), transparent 60%),
    radial-gradient(900px 500px at 100% 100%, rgba(34, 211, 238, 0.08), transparent 55%),
    #060b18;
}
.screen-stage {
  position: relative;
  flex: none;
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  transform-origin: center center;
  background:
    linear-gradient(180deg, rgba(10, 20, 38, 0.6) 0%, rgba(6, 11, 24, 0.9) 100%);
}
.screen-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 400px 1fr 400px;
  gap: 14px;
  margin: 14px 0;
}
/* 值班“告警”布局：预警 + 摄像头状态 + 排行 三栏 */
.screen-main.layout-alerts {
  grid-template-columns: 1.4fr 1fr 1fr;
}
/* 展厅模式隐藏操作按钮 */
.screen-viewport.is-present :deep(.sh-actions) {
  display: none;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}
.p-kpi {
  flex: 0 0 auto;
}
.grow {
  flex: 1;
  min-height: 0;
}
.grow-trend {
  flex: 1.55;
  min-height: 0;
}
.grow-alert {
  flex: 1.15;
  min-height: 0;
}
/* 预警插播横幅 */
.alert-banner {
  position: absolute;
  top: 92px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.95), rgba(249, 115, 22, 0.92));
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: 0 0 34px rgba(239, 68, 68, 0.65);
  font-size: 17px;
  letter-spacing: 1px;
  white-space: nowrap;
}
.ab-pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.8);
  animation: abPulse 1s infinite;
}
@keyframes abPulse {
  70% {
    box-shadow: 0 0 0 10px rgba(255, 255, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
  }
}
.ab-tag {
  padding: 2px 8px;
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.25);
  font-size: 13px;
  font-weight: 700;
}
.ab-type {
  font-weight: 800;
  font-size: 19px;
}
.ab-cam {
  font-weight: 600;
}
.ab-time {
  font-size: 13px;
  opacity: 0.85;
  font-variant-numeric: tabular-nums;
}
.banner-enter-active,
.banner-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}
.banner-enter-from,
.banner-leave-to {
  opacity: 0;
  transform: translate(-50%, -16px);
}

.screen-foot {
  flex-shrink: 0;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #45628c;
  letter-spacing: 0.5px;
}
.sf-left,
.sf-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.sf-sep {
  color: #2b3f60;
}
.sf-live {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.9);
  animation: sfpulse 1.8s infinite;
}
@keyframes sfpulse {
  50% {
    opacity: 0.3;
  }
}
.sf-ok {
  color: #22c55e;
}
.sf-error {
  color: #ef4444;
}
.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #060b18;
  color: #7d93b5;
  font-size: 14px;
  letter-spacing: 1px;
  z-index: 20;
}
.lm-ring {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 3px solid rgba(79, 156, 255, 0.2);
  border-top-color: #22d3ee;
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
