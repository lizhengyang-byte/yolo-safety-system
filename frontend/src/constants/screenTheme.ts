/** 智慧大屏（深色驻场屏）设计令牌与 ECharts 视觉配置。
 *  与后台浅色主题（variables.css）互不影响，仅大屏路由使用。 */

export const SCREEN = {
  bg1: "#060b18",
  bg2: "#0a1426",
  bg3: "#0d1c33",
  panel: "rgba(15, 29, 54, 0.55)",
  panelSolid: "#0e1e38",
  border: "rgba(79, 156, 255, 0.28)",
  borderSoft: "rgba(79, 156, 255, 0.14)",
  text1: "#e6f1ff",
  text2: "#9fb3d1",
  text3: "#5b7194",
  brand: "#4f9cff",
  brandDeep: "#2f6bff",
  cyan: "#22d3ee",
  danger: "#ef4444",
  warning: "#f59e0b",
  success: "#22c55e",
  purple: "#8b5cf6",
  palette: ["#2f6bff", "#22d3ee", "#f59e0b", "#ef4444", "#22c55e", "#8b5cf6"],
};

export const AXIS_LABEL = { color: "#7d93b5", fontSize: 12 };

export const AXIS_LINE = { lineStyle: { color: "rgba(79,156,255,0.18)" } };

export const SPLIT_LINE = {
  lineStyle: { color: "rgba(79,156,255,0.10)", type: "dashed" as const },
};

export const TOOLTIP = {
  backgroundColor: "rgba(6,12,24,0.94)",
  borderColor: "rgba(79,156,255,0.35)",
  borderWidth: 1,
  padding: [8, 12] as [number, number],
  textStyle: { color: "#e6f1ff", fontSize: 12 },
  extraCssText: "border-radius:10px;box-shadow:0 10px 28px rgba(0,0,0,.45);",
};

/** 违规类型 -> 大屏颜色（与常量 VIOLATION_TYPE_MAP 顺序对应） */
export const TYPE_COLORS: Record<string, string> = {
  no_helmet: "#ef4444",
  no_vest: "#f59e0b",
  no_mask: "#8b5cf6",
  fire: "#ff5a1f",
  smoke: "#94a3b8",
  zone_intrusion: "#d946ef",
};
