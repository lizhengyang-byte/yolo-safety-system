import request from "@/utils/request";

export interface DemoDetection {
  cls_id: number;
  cls_name: string;
  conf: number;
  box: [number, number, number, number];
}

export interface DemoResult {
  detections: DemoDetection[];
  violations: string[];
  snapshot_url: string | null;
}

export interface DemoStatus {
  model_loaded: boolean;
  model_path: string | null;
  device: string;
  conf_threshold: number;
}

/** 演示环境自检：模型是否已加载 */
export function demoStatus() {
  return request.get("/api/demo/status") as Promise<DemoStatus>;
}

/**
 * 上传一帧做检测。
 * - conf：置信度阈值覆盖（灵敏度滑块；不传用后端默认值）
 * - noSave：true 时只检测不入库（实时监控页 AI 叠加用）
 */
export function demoDetect(file: Blob, opts?: { conf?: number; noSave?: boolean }) {
  const fd = new FormData();
  fd.append("file", file, "frame.jpg");
  if (opts?.conf != null) fd.append("conf", String(opts.conf));
  if (opts?.noSave) fd.append("no_save", "true");
  return request.post("/api/demo/detect", fd) as Promise<DemoResult>;
}
