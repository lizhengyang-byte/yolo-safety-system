<template>
  <div>
    <el-card class="demo-card">
      <template #header>
        <div class="card-head-row">
          <div class="card-head-title">
            <span class="ico"><el-icon><Camera /></el-icon></span>
            临时演示（笔记本摄像头 / 本地视频）
          </div>
          <div class="actions">
            <el-select
              v-model="deviceId"
              placeholder="选择摄像头"
              class="device-select"
              @change="onDeviceChange"
            >
              <el-option
                v-for="d in devices"
                :key="d.deviceId"
                :label="d.label || `摄像头 ${d.deviceId.slice(0, 6)}`"
                :value="d.deviceId"
              />
            </el-select>
            <el-button v-if="!running" type="primary" @click="start">
              <el-icon class="btn-ico"><VideoPlay /></el-icon>开始演示（摄像头）
            </el-button>
            <el-button v-if="!running" @click="videoInputRef?.click()">
              <el-icon class="btn-ico"><VideoCamera /></el-icon>本地视频检测
            </el-button>
            <el-button v-if="!running" @click="selfCheck">
              <el-icon class="btn-ico"><CircleCheck /></el-icon>环境自检
            </el-button>
            <el-button v-else type="danger" @click="stop">
              <el-icon class="btn-ico"><SwitchButton /></el-icon>停止演示
            </el-button>
            <el-button v-if="running" @click="toggleFullscreen">
              <el-icon class="btn-ico"><FullScreen /></el-icon>全屏演示
            </el-button>
            <input
              ref="videoInputRef"
              type="file"
              accept="video/*"
              style="display: none"
              @change="onVideoPicked"
            />
          </div>
        </div>
      </template>

      <!-- 首次使用引导 -->
      <el-collapse v-if="!running && showGuide" class="guide-collapse">
        <el-collapse-item name="guide">
          <template #title>
            <span class="guide-title"><el-icon><Reading /></el-icon>演示使用指引（3 步）</span>
          </template>
          <el-steps :active="3" simple class="guide-steps">
            <el-step title="授权摄像头" description="点「开始演示」，浏览器会请求摄像头权限，选择允许" />
            <el-step title="实时识别" description="画面自动叠加检测框：红=违规、绿=合规穿戴、蓝=其他目标" />
            <el-step title="违规留痕" description="出现违规自动抓拍标注图入库，可在「违规记录」「安全日志」查看" />
          </el-steps>
        </el-collapse-item>
      </el-collapse>

      <!-- 演示参数（运行时可调） -->
      <div v-if="running" class="controls">
        <div class="ctrl">
          <span class="label">AI 灵敏度（置信度阈值）</span>
          <el-slider v-model="confSlider" :min="0.1" :max="0.9" :step="0.05" class="slider" />
        </div>
        <div class="ctrl">
          <el-switch v-model="onlyViolations" active-text="只看违规" />
        </div>
        <div class="ctrl">
          <el-switch v-model="mirrored" active-text="镜像画面" />
        </div>
        <div class="ctrl">
          <span class="label">画质</span>
          <el-select v-model="quality" class="quality-select">
            <el-option label="自动" value="auto" />
            <el-option label="720p" value="720" />
            <el-option label="480p" value="480" />
            <el-option label="360p" value="360" />
          </el-select>
        </div>
      </div>

      <div ref="stageRef" class="stage" v-show="running">
        <video ref="videoRef" autoplay muted playsinline :class="{ mirrored }"></video>
        <canvas ref="canvasRef"></canvas>
        <div v-if="violations.length" class="warn-tag">
          <el-icon><WarningFilled /></el-icon>
          <span>检测到违规：{{ violationText }}</span>
        </div>
        <div v-else-if="detectCount > 0" class="ok-tag">
          <span class="ok-dot"></span>检测中... 最近帧无违规
        </div>
        <div v-if="sourceMode === 'video'" class="src-tag">本地视频</div>
        <div v-if="running && detectCount > 0" class="fps-tag">
          延迟 {{ latency.toFixed(0) }}ms · {{ (1000 / latency).toFixed(1) }} 帧/s
        </div>
        <!-- 模型加载遮罩 -->
        <div v-if="modelLoading" class="loading-overlay">
          <div class="spinner"></div>
          <div class="loading-text">正在加载 AI 模型（首次约 10–30 秒），请稍候…</div>
        </div>
      </div>
      <el-empty
        v-if="!running"
        description="点击「开始演示（摄像头）」调用笔记本摄像头，或「本地视频检测」选择视频文件实时识别"
      />

      <!-- 演示统计 -->
      <div v-if="running" class="stats">
        <div class="stat-item">
          <div class="num tnum">{{ detectCount }}</div>
          <div class="label">检测帧数</div>
        </div>
        <div class="stat-item warn">
          <div class="num tnum">{{ violationCount }}</div>
          <div class="label">违规次数</div>
        </div>
        <div v-for="t in typeCounts" :key="t.type" class="stat-item">
          <div class="num tnum">{{ t.count }}</div>
          <div class="label">{{ t.label }}</div>
        </div>
        <div class="stat-item blue">
          <div class="num tnum">{{ (1000 / latency).toFixed(1) }}</div>
          <div class="label">帧率（帧/s）</div>
        </div>
      </div>

      <el-alert
        v-if="running"
        class="demo-tip"
        type="info"
        :closable="false"
        title="演示模式：前端取帧 -> 后端 YOLO 检测 -> 违规自动抓拍标注图入库，流程与正式链路一致。"
      />
    </el-card>

    <!-- 本次演示违规时间线 -->
    <el-card v-if="snapshots.length" class="timeline-card">
      <template #header>
        <div class="card-head-title">
          <span class="ico"><el-icon><Picture /></el-icon></span>
          本次演示抓拍留痕（已入库）
        </div>
      </template>
      <div class="timeline">
        <el-image
          v-for="(s, i) in snapshots"
          :key="s.url + i"
          :src="s.url"
          fit="cover"
          class="thumb"
          :preview-src-list="snapshots.map((x) => x.url)"
          :initial-index="i"
          preview-teleported
        >
          <template #placeholder>
            <div class="thumb-placeholder">加载中</div>
          </template>
          <template #error>
            <div class="thumb-placeholder">加载失败</div>
          </template>
        </el-image>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { demoDetect, demoStatus, type DemoDetection } from "@/api/demo";
import { drawDetections } from "@/utils/draw";
import { VIOLATION_TYPE_MAP } from "@/constants/violations";

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const videoInputRef = ref<HTMLInputElement | null>(null);
const stageRef = ref<HTMLDivElement | null>(null);

const running = ref(false);
const showGuide = ref(true);
const devices = ref<MediaDeviceInfo[]>([]);
const deviceId = ref("");
const snapshots = ref<{ url: string; time: string }[]>([]);
const detectCount = ref(0);
const boxes = ref<DemoDetection[]>([]);
const violations = ref<string[]>([]);
const sourceMode = ref<"camera" | "video">("camera");
const modelLoading = ref(false);
const latency = ref(300);
const confSlider = ref(0.5);
const onlyViolations = ref(false);
const mirrored = ref(true);
const quality = ref("auto");

// 演示统计
const violationCount = ref(0);
const typeCounts = ref<{ type: string; label: string; count: number }[]>([]);

let stream: MediaStream | null = null;
let timer: number | null = null;
let offCanvas: HTMLCanvasElement | null = null;
let videoUrl: string | null = null;
let inFlight = false;

const violationText = computed(() =>
  violations.value.map((v) => VIOLATION_TYPE_MAP[v] || v).join("、")
);

function getVideoHeight(): number | undefined {
  const q = Number(quality.value);
  return Number.isNaN(q) || quality.value === "auto" ? undefined : q;
}

// ---------- 摄像头错误分类提示 ----------
function cameraErrorText(e: any): string {
  const name = e?.name || "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError")
    return "摄像头权限被拒绝：点击地址栏右侧的摄像头图标允许访问，或检查 Windows 设置 > 隐私和安全性 > 摄像头";
  if (name === "NotFoundError" || name === "DevicesNotFoundError")
    return "未找到摄像头设备：请检查设备连接，或改用「本地视频检测」";
  if (name === "NotReadableError" || name === "TrackStartError")
    return "摄像头被其他程序占用（如会议软件），请关闭后重试";
  if (name === "SecurityError" || name === "InsecureContextError")
    return "当前环境不安全：请通过 http://localhost:3000 访问本系统（不能用局域网 IP）";
  return "无法访问摄像头：" + (e?.message || name || "未知错误");
}

// ---------- 环境自检 ----------
async function selfCheck() {
  const checks: { item: string; ok: boolean; detail: string }[] = [];

  // 1. 摄像头 API
  const hasMedia = !!navigator.mediaDevices?.getUserMedia;
  checks.push({
    item: "浏览器摄像头支持",
    ok: hasMedia,
    detail: hasMedia ? "支持 getUserMedia" : "不支持，请用最新版 Chrome / Edge",
  });

  // 2. 后端连通
  try {
    await demoStatus();
    checks.push({ item: "后端服务连通", ok: true, detail: "已连接" });
  } catch {
    checks.push({ item: "后端服务连通", ok: false, detail: "无法连接后端（8000 端口）" });
  }

  // 3. 模型就绪
  try {
    const st = await demoStatus();
    checks.push({
      item: "AI 模型就绪",
      ok: st.model_loaded,
      detail: st.model_loaded
        ? `已加载（${st.device}）`
        : `未加载（首次检测时加载，路径：${st.model_path || "未找到 ppe.pt"}）`,
    });
  } catch {
    checks.push({ item: "AI 模型就绪", ok: false, detail: "无法获取模型状态" });
  }

  const lines = checks
    .map((c) => `${c.ok ? "✅" : "❌"} ${c.item}：${c.detail}`)
    .join("\n");
  await ElMessageBox.alert(lines, "环境自检结果", {
    confirmButtonText: "知道了",
    dangerouslyUseHTMLString: false,
  });
}

// ---------- 枚举摄像头设备 ----------
async function loadDevices() {
  try {
    const all = await navigator.mediaDevices.enumerateDevices();
    devices.value = all.filter((d) => d.kind === "videoinput");
    if (devices.value.length && !deviceId.value) {
      deviceId.value = devices.value[0].deviceId;
    }
  } catch {
    ElMessage.warning("无法枚举摄像头设备");
  }
}

// ---------- 启动 / 停止 ----------
function resetState() {
  boxes.value = [];
  violations.value = [];
  snapshots.value = [];
  detectCount.value = 0;
  violationCount.value = 0;
  typeCounts.value = [];
  latency.value = 300;
  inFlight = false;
}

function setupCanvas(video: HTMLVideoElement) {
  const canvas = canvasRef.value!;
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  offCanvas = document.createElement("canvas");
  offCanvas.width = canvas.width;
  offCanvas.height = canvas.height;
}

function stopStream() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  inFlight = false;
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  const video = videoRef.value;
  if (video) {
    video.srcObject = null;
    if (videoUrl) {
      video.pause();
      video.removeAttribute("src");
      URL.revokeObjectURL(videoUrl);
      videoUrl = null;
    }
  }
}

async function start() {
  stopStream();
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.error("当前浏览器不支持摄像头调用，请使用最新版 Chrome / Edge");
    return;
  }
  let stream2: MediaStream;
  try {
    // 视频约束：所选设备不可用时自动回退其他摄像头；画质按选择限制高度
    const videoConstraints: MediaTrackConstraints = {};
    if (deviceId.value) videoConstraints.deviceId = { ideal: deviceId.value };
    const height = getVideoHeight();
    if (height) videoConstraints.height = { ideal: height };
    stream2 = await navigator.mediaDevices.getUserMedia({
      video: videoConstraints,
      audio: false,
    });
  } catch (e) {
    ElMessage.error(cameraErrorText(e));
    return;
  }
  stream = stream2;

  const video = videoRef.value!;
  sourceMode.value = "camera";
  video.srcObject = stream;
  video.muted = true;
  try {
    await video.play();
  } catch (e) {
    stop();
    ElMessage.error("视频播放失败：" + (e as Error).message);
    return;
  }

  setupCanvas(video);
  await loadDevices();
  resetState();
  running.value = true;

  // 模型加载提示：已加载则立即隐藏，否则保持到首个检测结果返回
  modelLoading.value = true;
  try {
    const st = await demoStatus();
    if (st.model_loaded) modelLoading.value = false;
  } catch {
    /* 状态接口失败时依赖首个检测结果收起遮罩 */
  }

  // 每 500ms 取一帧上传检测
  timer = window.setInterval(detect, 500);
}

async function onVideoPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = ""; // 允许重复选择同一文件
  if (!file) return;
  stopStream();

  const video = videoRef.value!;
  videoUrl = URL.createObjectURL(file);
  video.srcObject = null;
  video.src = videoUrl;
  video.muted = true;
  video.loop = true; // 循环播放，持续演示
  sourceMode.value = "video";
  try {
    await video.play();
  } catch (err) {
    stop();
    ElMessage.error("视频播放失败：" + (err as Error).message);
    return;
  }

  setupCanvas(video);
  resetState();
  running.value = true;

  modelLoading.value = true;
  try {
    const st = await demoStatus();
    if (st.model_loaded) modelLoading.value = false;
  } catch {
    /* 同上 */
  }
  timer = window.setInterval(detect, 500);
}

function stop() {
  stopStream();
  running.value = false;
  modelLoading.value = false;
  const ctx = canvasRef.value?.getContext("2d");
  ctx?.clearRect(0, 0, canvasRef.value!.width, canvasRef.value!.height);
}

async function onDeviceChange() {
  if (running.value && sourceMode.value === "camera") {
    stop();
    await start();
  }
}

function toggleFullscreen() {
  const stage = stageRef.value;
  if (!stage) return;
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  } else {
    stage.requestFullscreen?.().catch(() => {
      ElMessage.warning("浏览器不允许进入全屏，请检查权限设置");
    });
  }
}

// ---------- 检测 + 绘制 ----------
async function detect() {
  const video = videoRef.value!;
  if (inFlight) return; // 上一帧未返回则跳过本帧，避免请求堆积
  // 视频未就绪时跳过，避免 drawImage 抛错
  if (!video.videoWidth || video.readyState < 2) return;
  const offCtx = offCanvas!.getContext("2d")!;
  offCtx.drawImage(video, 0, 0, offCanvas!.width, offCanvas!.height);

  offCanvas!.toBlob(async (blob) => {
    if (!blob) return;
    inFlight = true;
    const t0 = performance.now();
    try {
      const res = await demoDetect(blob, { conf: confSlider.value });
      latency.value = latency.value * 0.7 + (performance.now() - t0) * 0.3;
      modelLoading.value = false; // 首个结果返回，模型已就绪

      boxes.value = res.detections;
      violations.value = res.violations;
      detectCount.value += 1;

      // 统计：违规次数与分类型计数
      if (res.violations.length) {
        violationCount.value += 1;
        for (const v of res.violations) {
          const item = typeCounts.value.find((t) => t.type === v);
          if (item) item.count += 1;
          else
            typeCounts.value.push({
              type: v,
              label: VIOLATION_TYPE_MAP[v] || v,
              count: 1,
            });
        }
      }

      // 抓拍时间线（去重）
      if (res.snapshot_url && !snapshots.value.some((s) => s.url === res.snapshot_url)) {
        snapshots.value.push({
          url: res.snapshot_url,
          time: new Date().toLocaleTimeString("zh-CN", { hour12: false }),
        });
      }
      drawDetections(canvasRef.value!, res.detections, res.violations, onlyViolations.value);
    } catch (e) {
      // 模型未就绪等场景：提示一次后静默重试
      const msg = (e as any)?.response?.data?.detail || (e as Error)?.message;
      if (msg && !modelLoading.value) {
        ElMessage.warning(typeof msg === "string" ? msg : "检测失败，请稍后重试");
        modelLoading.value = true;
      }
      console.warn("演示检测失败", e);
    } finally {
      inFlight = false;
    }
  }, "image/jpeg", 0.85);
}

loadDevices();
onUnmounted(stop);
</script>

<style scoped>
.demo-card :deep(.el-card__body) {
  padding: 18px 20px 20px;
}
.card-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.card-head-title {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-weight: 600;
  color: var(--text-1);
}
.card-head-title .ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--brand-100), #eef4ff);
  color: var(--brand-500);
  font-size: 15px;
}
.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.device-select {
  width: 200px;
}
.btn-ico {
  margin-right: 5px;
}

/* 引导 */
.guide-collapse {
  margin-bottom: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-soft);
  padding: 0 16px;
}
.guide-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-weight: 600;
  color: var(--text-1);
}
.guide-steps {
  padding: 8px 0 12px;
}

/* 参数栏 */
.controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 22px;
  padding: 14px 18px;
  background: linear-gradient(180deg, #f8fafd, #f2f6fc);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 14px;
}
.ctrl {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ctrl .label {
  font-size: 13px;
  color: var(--text-2);
  white-space: nowrap;
}
.slider {
  width: 180px;
}
.quality-select {
  width: 110px;
}

/* 舞台 */
.stage {
  position: relative;
  width: 100%;
  max-width: 760px;
  aspect-ratio: 4 / 3;
  background: radial-gradient(circle at 50% 40%, #101826, #05070c);
  margin: 0 auto;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.24);
  box-shadow: inset 0 0 46px rgba(0, 0, 0, 0.6), var(--shadow-md);
}
video,
canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
video.mirrored {
  transform: scaleX(-1); /* 摄像头画面镜像，符合自拍习惯 */
}
.warn-tag,
.ok-tag,
.src-tag,
.fps-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 15px;
  border-radius: 999px;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  z-index: 2;
  backdrop-filter: blur(6px);
}
.warn-tag {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(249, 115, 22, 0.95));
  box-shadow: 0 8px 22px rgba(239, 68, 68, 0.4);
}
.ok-tag {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  font-weight: 500;
}
.ok-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}
.src-tag {
  right: 12px;
  left: auto;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  font-weight: 500;
}
.fps-tag {
  right: 12px;
  left: auto;
  top: 54px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  font-weight: 400;
  font-size: 12px;
}
.loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(5, 8, 16, 0.78);
  backdrop-filter: blur(3px);
  z-index: 3;
}
.spinner {
  width: 52px;
  height: 52px;
  border: 4px solid rgba(255, 255, 255, 0.18);
  border-top-color: var(--brand-400);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}
.loading-text {
  margin-top: 18px;
  color: #dbe7ff;
  font-size: 15px;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 统计磁贴 */
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}
.stat-item {
  flex: 1;
  min-width: 96px;
  text-align: center;
  padding: 14px 10px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-xs);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
.num {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-1);
  line-height: 1.1;
}
.stat-item.warn .num {
  color: var(--danger);
}
.stat-item.blue .num {
  color: var(--brand-500);
}
.label {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 4px;
}
.demo-tip {
  margin-top: 16px;
  border-radius: var(--radius);
}

/* 时间线 */
.timeline-card {
  margin-top: 16px;
}
.timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.thumb {
  width: 152px;
  height: 96px;
  border-radius: 10px;
  cursor: pointer;
  overflow: hidden;
  border: 1px solid var(--border);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.thumb:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: var(--shadow-md);
}
.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--text-3);
  background: var(--surface-muted);
}
</style>
