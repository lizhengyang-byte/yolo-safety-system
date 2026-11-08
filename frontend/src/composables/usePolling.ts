import { onBeforeUnmount, onMounted } from "vue";

/** 统一轮询：防重入 + 页面隐藏自动暂停 + 恢复立即刷新。
 *  task 内部自行捕获异常，这里只负责调度，避免未捕获 Promise 报错刷屏。 */
export function usePolling(
  task: () => void | Promise<void>,
  interval = 15000,
  immediate = true
) {
  let timer: number | null = null;
  let running = false;

  async function run() {
    if (document.hidden || running) return;
    running = true;
    try {
      await task();
    } catch {
      /* 由调用方负责展示错误状态 */
    } finally {
      running = false;
    }
  }

  function start() {
    stop();
    timer = window.setInterval(run, interval);
  }

  function stop() {
    if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }
  }

  function onVisible() {
    if (!document.hidden) run();
  }

  onMounted(() => {
    if (immediate) run();
    start();
    document.addEventListener("visibilitychange", onVisible);
  });

  onBeforeUnmount(() => {
    stop();
    document.removeEventListener("visibilitychange", onVisible);
  });

  return { run, start, stop };
}
