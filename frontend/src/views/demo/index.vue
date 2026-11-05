<template>
  <div>
    <el-card>
      <template #header>
        <div class="header">
          <span>临时演示（直接调用笔记本摄像头）</span>
          <div class="actions">
            <el-select
              v-model="deviceId"
              placeholder="选择摄像头"
              style="width: 220px; margin-right: 12px"
              @change="onDeviceChange"
            >
              <el-option
                v-for="d in devices"
                :key="d.deviceId"
                :label="d.label || `摄像头 ${d.deviceId.slice(0, 6)}`"
                :value="d.deviceId"
              />
            </el-select>
            <el-button v-if="!running" type="primary" @click="start">开始演示</el-button>
            <el-button v-else type="danger" @click="stop">停止演示</el-button>
          </div>
        </div>
      </template>

      <div class="stage" v-show="running">
        <video ref="videoRef" autoplay muted playsinline></video>
        <canvas ref="canvasRef"></canvas>
        <div v-if="violations.length" class="warn-tag">
          ⚠️ 检测到违规：{{ violationText }}
        </div>
        <div v-else-if="detectCount > 0" class="ok-tag">
          检测中... 最近帧无违规
        </div>
      </div>
      <el-empty v-if="!running" description="点击「开始演示」调用笔记本摄像头实时识别" />

      <el-alert
        v-if="running"
        type="info"
        :closable="false"
        style="margin-top: 16px"
        title="演示模式：前端取笔记本摄像头帧 -> 后端 YOLO 检测 -> 违规自动抓拍入库，流程与正式链路一致。"
      />
    </el-card>

    <el-card v-if="lastSnapshot" style="margin-top: 16px">
      <template #header>最近抓拍留痕（已入库）</template>
      <el-image
        :src="lastSnapshot"
        fit="contain"
        style="max-width: 420px; border-radius: 6px"
        :preview-src-list="[lastSnapshot]"
        preview-teleported
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { demoDetect, type DemoDetection } from "@/api/demo";

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);

const running = ref(false);
const devices = ref<MediaDeviceInfo[]>([]);
const deviceId = ref("");
const lastSnapshot = ref<string | null>(null);
const detectCount = ref(0);
const boxes = ref<DemoDetection[]>([]);
const violations = ref<string[]>([]);

let stream: MediaStream | null = null;
let timer: number | null = null;
let offCanvas: HTMLCanvasElement | null = null;

const typeMap: Record<string, string> = {
  no_helmet: "未戴安全帽",
  no_vest: "未穿安全马甲",
  no_mask: "未戴口罩",
};
const violationText = computed(() =>
  violations.value.map((v) => typeMap[v] || v).join("、")
);

// ---------- 枚举摄像头设备 ----------
async function loadDevices() {
  try {
    const all = await navigator.mediaDevices.enumerateDevices();
    devices.value = all.filter((d) => d.kind === "videoinput");
    if (devices.value.length && !deviceId.value) {
      deviceId.value = devices.value[0].deviceId;
    }
  } catch (e) {
    ElMessage.warning("无法枚举摄像头设备");
  }
}

// ---------- 启动 / 停止 ----------
async function start() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: deviceId.value ? { exact: deviceId.value } : undefined },
      audio: false,
    });
  } catch (e) {
    ElMessage.error("无法访问摄像头，请检查权限（需 HTTPS 或 localhost）");
    return;
  }
  running.value = true;
  boxes.value = [];
  violations.value = [];
  lastSnapshot.value = null;
  detectCount.value = 0;

  await loadDevices();
  const video = videoRef.value!;
  video.srcObject = stream;
  await video.play();

  // 画布与视频同尺寸
  const canvas = canvasRef.value!;
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;

  offCanvas = document.createElement("canvas");
  offCanvas.width = canvas.width;
  offCanvas.height = canvas.height;

  // 每 500ms 取一帧上传检测
  timer = window.setInterval(detect, 500);
}

function stop() {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  if (videoRef.value) videoRef.value.srcObject = null;
  running.value = false;
  const ctx = canvasRef.value?.getContext("2d");
  ctx?.clearRect(0, 0, canvasRef.value!.width, canvasRef.value!.height);
}

async function onDeviceChange() {
  if (running.value) {
    stop();
    await start();
  }
}

// ---------- 检测 + 绘制 ----------
async function detect() {
  const video = videoRef.value!;
  const offCtx = offCanvas!.getContext("2d")!;
  offCtx.drawImage(video, 0, 0, offCanvas!.width, offCanvas!.height);

  offCanvas!.toBlob(async (blob) => {
    if (!blob) return;
    try {
      const res = await demoDetect(blob);
      boxes.value = res.detections;
      violations.value = res.violations;
      if (res.snapshot_url) lastSnapshot.value = res.snapshot_url;
      detectCount.value += 1;
      draw(res.detections, res.violations);
    } catch (e) {
      console.warn("演示检测失败", e);
    }
  }, "image/jpeg", 0.85);
}

function draw(dets: DemoDetection[], viols: string[]) {
  const canvas = canvasRef.value!;
  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 违规类型集合（用于把对应装备框标红）
  const vioSet = new Set(viols);
  const equipOf: Record<string, string> = {
    no_helmet: "helmet",
    no_vest: "vest",
    no_mask: "mask",
  };

  for (const d of dets) {
    const [x1, y1, x2, y2] = d.box;
    const w = x2 - x1;
    const h = y2 - y1;

    let color = "#409eff";
    if (d.cls_name === "person") color = "#67c23a";
    // 若该装备缺失（违规），标红对应装备框
    for (const v of vioSet) {
      if (d.cls_name === equipOf[v]) color = "#f56c6c";
    }

    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x1, y1, w, h);

    const label = `${d.cls_name} ${(d.conf * 100).toFixed(0)}%`;
    ctx.fillStyle = color;
    ctx.font = "bold 16px sans-serif";
    const tw = ctx.measureText(label).width + 10;
    ctx.fillRect(x1, y1 - 22, tw, 22);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x1 + 5, y1 - 5);
  }
}

loadDevices();
onUnmounted(stop);
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.actions {
  display: flex;
  align-items: center;
}
.stage {
  position: relative;
  width: 100%;
  max-width: 720px;
  aspect-ratio: 4 / 3;
  background: #000;
  margin: 0 auto;
}
video,
canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
video {
  transform: scaleX(-1); /* 镜像，符合自拍习惯 */
}
.warn-tag,
.ok-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 6px 14px;
  border-radius: 6px;
  color: #fff;
  font-weight: bold;
  z-index: 2;
}
.warn-tag {
  background: #f56c6c;
}
.ok-tag {
  background: #909399;
}
</style>
