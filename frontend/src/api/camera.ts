import request from "@/utils/request";

export interface Camera {
  id: number;
  name: string;
  location: string;
  rtsp_url: string;
  status: string;
  enabled: boolean;
  created_at: string;
}

export interface CameraTestResult {
  ok: boolean;
  message: string;
}

export function listCameras() {
  return request.get("/api/cameras") as Promise<Camera[]>;
}

export function createCamera(data: Partial<Camera>) {
  return request.post("/api/cameras", data) as Promise<Camera>;
}

export function updateCamera(id: number, data: Partial<Camera>) {
  return request.put(`/api/cameras/${id}`, data) as Promise<Camera>;
}

export function deleteCamera(id: number) {
  return request.delete(`/api/cameras/${id}`) as Promise<{ message: string }>;
}

/** 试拉 RTSP 流验证连通性（后端 8 秒超时） */
export function testCameraConnection(rtspUrl: string) {
  return request.post("/api/cameras/test", { rtsp_url: rtspUrl }) as Promise<CameraTestResult>;
}
