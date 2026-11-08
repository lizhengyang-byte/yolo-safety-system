<template>
  <section class="panel-frame">
    <span class="pf-corner tl"></span>
    <span class="pf-corner tr"></span>
    <span class="pf-corner bl"></span>
    <span class="pf-corner br"></span>
    <header class="pf-head">
      <div class="pf-title">
        <span class="pf-bar"></span>
        <span class="pf-text">{{ title }}</span>
        <span v-if="hint" class="pf-hint">{{ hint }}</span>
      </div>
      <div class="pf-extra"><slot name="extra" /></div>
    </header>
    <div class="pf-body"><slot /></div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ title: string; hint?: string }>();
</script>

<style scoped>
.panel-frame {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 14px 16px 12px;
  border-radius: 10px;
  background: linear-gradient(
    160deg,
    rgba(19, 38, 70, 0.65) 0%,
    rgba(10, 22, 43, 0.55) 100%
  );
  border: 1px solid rgba(79, 156, 255, 0.22);
  box-shadow: inset 0 0 24px rgba(47, 107, 255, 0.08), 0 6px 20px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}
.pf-corner {
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: rgba(79, 156, 255, 0.85);
  border-style: solid;
  pointer-events: none;
}
.pf-corner.tl {
  top: 6px;
  left: 6px;
  border-width: 2px 0 0 2px;
}
.pf-corner.tr {
  top: 6px;
  right: 6px;
  border-width: 2px 2px 0 0;
}
.pf-corner.bl {
  bottom: 6px;
  left: 6px;
  border-width: 0 0 2px 2px;
}
.pf-corner.br {
  bottom: 6px;
  right: 6px;
  border-width: 0 2px 2px 0;
}
.pf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(79, 156, 255, 0.12);
  flex-shrink: 0;
}
.pf-title {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}
.pf-bar {
  width: 3px;
  height: 15px;
  border-radius: 2px;
  background: linear-gradient(180deg, #22d3ee, #2f6bff);
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.9);
  flex-shrink: 0;
}
.pf-text {
  color: #e6f1ff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pf-hint {
  color: #5b7194;
  font-size: 12px;
  white-space: nowrap;
}
.pf-extra {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.pf-body {
  position: relative;
  flex: 1;
  min-height: 0;
}
</style>
