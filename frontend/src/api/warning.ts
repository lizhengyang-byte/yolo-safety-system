import request from "@/utils/request";

export interface WarningRule {
  id: number;
  name: string;
  camera_id: number | null;
  violation_type: string | null;
  threshold: number;
  window_minutes: number;
  enabled: boolean;
  created_at: string;
}

export interface WarningEvent {
  id: number;
  rule_id: number | null;
  camera_id: number;
  camera_name: string;
  violation_type: string;
  count: number;
  triggered_at: string;
  is_read: boolean;
}

export interface WarningEventPage {
  total: number;
  items: WarningEvent[];
}

export function listRules() {
  return request.get("/api/warnings/rules") as Promise<WarningRule[]>;
}

export function createRule(data: Partial<WarningRule>) {
  return request.post("/api/warnings/rules", data) as Promise<WarningRule>;
}

export function updateRule(id: number, data: Partial<WarningRule>) {
  return request.put(`/api/warnings/rules/${id}`, data) as Promise<WarningRule>;
}

export function deleteRule(id: number) {
  return request.delete(`/api/warnings/rules/${id}`) as Promise<WarningRule>;
}

export function listEvents(params: {
  page?: number;
  page_size?: number;
  unread_only?: boolean;
}) {
  return request.get("/api/warnings/events", { params }) as Promise<WarningEventPage>;
}

export function getUnreadCount() {
  return request.get("/api/warnings/unread-count") as Promise<{ count: number }>;
}

export function markRead(ids: number[]) {
  return request.post("/api/warnings/events/read", null, {
    params: { ids },
  }) as Promise<{ message: string }>;
}

export function markAllRead() {
  return request.post("/api/warnings/events/read-all") as Promise<{ message: string }>;
}
