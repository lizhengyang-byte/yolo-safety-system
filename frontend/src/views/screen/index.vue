<template>
  <div ref="rootRef" class="screen-viewport">
    <div class="screen-stage" :style="stageStyle">
      <ScreenHeader
        :online="data.online_cameras"
        :unread="unread"
        :is-fullscreen="isFullscreen"
        @toggle-fullscreen="toggleFullscreen"
        @exit="exitScreen"
      />

      <div class="screen-main">
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
      </div>

      <footer class="screen-foot">
        <span class="sf-left">
          <span class="sf-live"></span>
          数据更新：{{ lastUpdated || "--" }}
          <span class="sf-sep">|</span>
          每 15 秒自动刷新
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
import { useRouter } from "vue-router";
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
import { getDashboard, type DashboardData } from "@/api/violation";

const router = useRouter();
const { stageStyle } = useScreenScale(1920, 1080);

const days = ref(7);
const loaded = ref(false);
const error = ref("");
const lastUpdated = ref("");
const rootRef = ref<HTMLDivElement | null>(null);
const isFullscreen = ref(false);

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

usePolling(load, 15000);

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

onMounted(() => document.addEventListener("fullscreenchange", onFsChange));
onBeforeUnmount(() => document.removeEventListener("fullscreenchange", onFsChange));
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
