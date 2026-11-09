import { onBeforeUnmount, onMounted, ref } from "vue";

/** 实时事件类型（与后端 /api/realtime/stream 的 event 名一致） */
export type RealtimeEvent = "violation" | "warning" | "camera_status";
type Handler = (data: any) => void;

const handlers: Record<RealtimeEvent, Set<Handler>> = {
  violation: new Set(),
  warning: new Set(),
  camera_status: new Set(),
};

const connected = ref(false);
let es: EventSource | null = null;
let refcount = 0;

function dispatch(type: RealtimeEvent, e: MessageEvent) {
  let data: any = null;
  try {
    data = JSON.parse(e.data);
  } catch {
    data = e.data;
  }
  handlers[type].forEach((h) => {
    try {
      h(data);
    } catch {
      /* 单个回调异常不影响其他订阅者 */
    }
  });
}

function connect() {
  if (es) return;
  const token = localStorage.getItem("token");
  if (!token || typeof EventSource === "undefined") {
    connected.value = false;
    return;
  }
  // 单例连接：看板 + 顶栏共用一条 SSE，避免重复连接
  es = new EventSource(`/api/realtime/stream?token=${encodeURIComponent(token)}`);
  es.onopen = () => {
    connected.value = true;
  };
  es.onerror = () => {
    // EventSource 会按服务端 retry 自动重连，这里仅更新状态
    connected.value = false;
  };
  (["violation", "warning", "camera_status"] as const).forEach((type) => {
    es!.addEventListener(type, (e) => dispatch(type, e as MessageEvent));
  });
}

function disconnect() {
  es?.close();
  es = null;
  connected.value = false;
}

/**
 * 订阅实时事件。多个组件可同时使用，内部共享一个 EventSource。
 * 用法：useRealtime({ violation: (d) => load(), warning: () => load() })
 */
export function useRealtime(map: Partial<Record<RealtimeEvent, Handler>>) {
  const entries = Object.entries(map) as [RealtimeEvent, Handler][];

  onMounted(() => {
    entries.forEach(([type, h]) => handlers[type].add(h));
    refcount += 1;
    connect();
  });

  onBeforeUnmount(() => {
    entries.forEach(([type, h]) => handlers[type].delete(h));
    refcount = Math.max(0, refcount - 1);
    if (refcount === 0) disconnect();
  });

  return { connected };
}
