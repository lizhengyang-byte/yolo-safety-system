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
