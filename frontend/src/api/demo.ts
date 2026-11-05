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

export function demoDetect(file: Blob) {
  const fd = new FormData();
  fd.append("file", file, "frame.jpg");
  return request.post("/api/demo/detect", fd) as Promise<DemoResult>;
}
