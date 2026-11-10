import request from "@/utils/request";

/** 危险区域（多边形 ROI，归一化坐标 0~1） */
export interface DangerZone {
  id: number;
  camera_id: number;
  zone_name: string;
  zone_type: string; // danger / pit / lifting / other
  polygon: number[][]; // [[x, y], ...] 归一化 0~1
  min_confidence: number;
  min_dwell_seconds: number;
  enabled: boolean;
  created_at: string;
}

export type DangerZoneInput = Omit<DangerZone, "id" | "created_at">;

export function listZones(cameraId?: number) {
  const params = cameraId != null ? { camera_id: cameraId } : {};
  return request.get("/api/zones", { params }) as Promise<DangerZone[]>;
}

export function createZone(data: DangerZoneInput) {
  return request.post("/api/zones", data) as Promise<DangerZone>;
}

export function updateZone(id: number, data: Partial<DangerZoneInput>) {
  return request.put(`/api/zones/${id}`, data) as Promise<DangerZone>;
}

export function deleteZone(id: number) {
  return request.delete(`/api/zones/${id}`) as Promise<{ message: string }>;
}

/** 区域类别中文名 */
export const ZONE_TYPE_LABELS: Record<string, string> = {
  danger: "配电房/危险区",
  pit: "基坑",
  lifting: "吊装区",
  other: "其他",
};
