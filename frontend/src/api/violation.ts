import request from "@/utils/request";

export interface Violation {
  id: number;
  camera_id: number;
  camera_name: string;
  violation_type: string;
  confidence: number;
  image_url: string;
  created_at: string;
}

export interface PageResult {
  total: number;
  items: Violation[];
}

export interface QueryParams {
  page?: number;
  page_size?: number;
  violation_type?: string;
  camera_id?: number;
  start?: string;
  end?: string;
}

export function listViolations(params: QueryParams) {
  return request.get("/api/violations", { params }) as Promise<PageResult>;
}

export function getStats() {
  return request.get("/api/logs/stats") as Promise<{
    total: number;
    detail: { type: string; count: number }[];
  }>;
}
