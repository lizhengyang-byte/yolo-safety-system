import request from "@/utils/request";

export interface MailConfig {
  enabled: boolean;
  host: string;
  port: number;
  user: string;
  password: string;
  ssl: boolean;
  starttls: boolean;
  from: string;
  to: string;
  has_password?: boolean;
}

export interface ReportConfig {
  warning_email_enabled: boolean;
  daily_enabled: boolean;
  daily_time: string;
  weekly_enabled: boolean;
  weekly_day: number;
  weekly_time: string;
  report_to: string;
  last_daily_sent: string;
  last_weekly_sent: string;
  effective_to?: string;
}

export function getMailConfig() {
  return request.get("/api/settings/mail") as Promise<MailConfig>;
}

export function updateMailConfig(data: Partial<MailConfig>) {
  return request.put("/api/settings/mail", data) as Promise<MailConfig>;
}

export function testMail() {
  return request.post("/api/settings/mail/test") as Promise<{
    ok: boolean;
    message: string;
  }>;
}

export function getReportConfig() {
  return request.get("/api/settings/report") as Promise<ReportConfig>;
}

export function updateReportConfig(data: Partial<ReportConfig>) {
  return request.put("/api/settings/report", data) as Promise<ReportConfig>;
}

export function sendReportNow(period: "daily" | "week" | "month") {
  return request.post("/api/settings/report/send", null, {
    params: { period },
  }) as Promise<{ message: string }>;
}

/** 生成报告 PDF 并通过邮件发送（导出后直接发邮件） */
export function emailReport(period: "week" | "month") {
  return request.post("/api/logs/report/email", null, {
    params: { period },
    timeout: 120000,
  }) as Promise<{ message: string; filename: string }>;
}
