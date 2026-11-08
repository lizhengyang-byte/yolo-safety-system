<template>
  <span class="count-up tnum">{{ display }}</span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{ value: number; duration?: number; decimals?: number }>(),
  { duration: 800, decimals: 0 }
);

function format(n: number) {
  if (props.decimals > 0) return n.toFixed(props.decimals);
  return Math.round(n).toLocaleString("en-US");
}

const display = ref(format(props.value));
let raf = 0;

function animate(from: number, to: number) {
  cancelAnimationFrame(raf);
  const reduce =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) {
    display.value = format(to);
    return;
  }
  const start = performance.now();
  const step = (now: number) => {
    const p = Math.min(1, (now - start) / props.duration);
    const eased = 1 - Math.pow(1 - p, 3);
    display.value = format(from + (to - from) * eased);
    if (p < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
}

watch(
  () => props.value,
  (v, old) => animate(old ?? 0, v)
);

onBeforeUnmount(() => cancelAnimationFrame(raf));
</script>

<style scoped>
.count-up {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}
</style>
