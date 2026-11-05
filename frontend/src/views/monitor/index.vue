<template>
  <el-card>
    <template #header>
      <div class="header">
        <span>实时监控预览</span>
        <el-select
          v-model="currentCam"
          placeholder="选择摄像头"
          style="width: 260px"
          @change="play"
        >
          <el-option
            v-for="c in cameras"
            :key="c.id"
            :label="`${c.name}（${c.location}）`"
            :value="c.id"
          />
        </el-select>
      </div>
    </template>

    <div class="player-wrap">
      <video ref="videoRef" class="player" controls autoplay muted></video>
      <div v-if="!currentCam" class="placeholder">请选择摄像头查看实时画面</div>
    </div>

    <el-alert
      title="说明：浏览器无法直接播放 RTSP，需经 MediaMTX 转换为 FLV/WebRTC。请将下方 flv 地址模板替换为你的 MediaMTX 实际地址。"
      type="info"
      :closable="false"
      style="margin-top: 16px"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import flvjs from "flv.js";
import { listCameras, type Camera } from "@/api/camera";

const cameras = ref<Camera[]>([]);
const currentCam = ref<number | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
let player: any = null;

// MediaMTX 默认 FLV 播放地址模板：http://<mediaserver>:8080/live/<stream-name>.flv
// 这里约定 stream 名为摄像头 ID，可按需修改
function buildFlvUrl(cameraId: number): string {
  const base = "http://localhost:8080/live";
  return `${base}/${cameraId}.flv`;
}

function destroyPlayer() {
  if (player) {
    player.destroy();
    player = null;
  }
}

function play() {
  if (!currentCam.value || !videoRef.value) return;
  destroyPlayer();
  if (flvjs.isSupported()) {
    player = flvjs.createPlayer({
      type: "flv",
      url: buildFlvUrl(currentCam.value),
      isLive: true,
      hasAudio: false,
    });
    player.attachMediaElement(videoRef.value);
    player.load();
    player.play();
  } else {
    console.warn("当前浏览器不支持 flv.js");
  }
}

onMounted(async () => {
  cameras.value = await listCameras();
});

onUnmounted(destroyPlayer);
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.player-wrap {
  position: relative;
  width: 100%;
  height: 480px;
  background: #000;
}
.player {
  width: 100%;
  height: 100%;
}
.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
}
</style>
