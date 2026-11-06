import request from "@/utils/request";
import type { DemoDetection } from "@/api/demo";

export interface Violation {
  id: number;
  camera_id: number;
  camera_name: string;
  violation_type: string;
  confidence: number;
  image_url: string;
  anno_url: string;
  detections: DemoDetection[] | null;
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

export interface TrendPoint {
  date: string;
  count: number;
}

export interface DashboardData {
  total: number;
  today: number;
  online_cameras: number;
  trend: TrendPoint[];
  types: { type: string; count: number }[];
  ranking: { name: string; count: number }[];
  /** 点位（安装位置）违规排行 */
  location_ranking: { location: string; count: number }[];
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

/** 数据看板聚合数据（总数 / 今日 / 趋势 / 类型分布 / 摄像头排行 / 点位排行）
 * @param days 统计窗口天数（默认 7，看板可切换 30 / 90 查看长期趋势）
 */
export function getDashboard(days = 7) {
  return request.get("/api/logs/dashboard", { params: { days } }) as Promise<DashboardData>;
}
