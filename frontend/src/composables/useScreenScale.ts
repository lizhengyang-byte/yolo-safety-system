import { computed, onBeforeUnmount, onMounted, ref, type CSSProperties } from "vue";

/** 以固定设计稿尺寸（默认 1920×1080）等比缩放，适配 2K / 4K / 拼接屏不变形。
 *  非 16:9 屏幕等比缩放后居中留边，不做拉伸。 */
export function useScreenScale(designWidth = 1920, designHeight = 1080) {
  const scale = ref(1);

  const stageStyle = computed<CSSProperties>(() => ({
    width: `${designWidth}px`,
    height: `${designHeight}px`,
    transform: `scale(${scale.value})`,
  }));

  function update() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    if (!w || !h) return;
    scale.value = Math.min(w / designWidth, h / designHeight);
  }

  onMounted(() => {
    update();
    window.addEventListener("resize", update);
  });
  onBeforeUnmount(() => {
    window.removeEventListener("resize", update);
  });

  return { scale, stageStyle, update };
}
