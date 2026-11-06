/** 违规类型与检测类别相关的共享常量（各页面统一引用，避免重复定义） */

/** 违规类型 key -> 中文名称（与后端 annotate.py 的 VIOLATION_LABELS 保持一致） */
export const VIOLATION_TYPE_MAP: Record<string, string> = {
  no_helmet: "未戴安全帽",
  no_vest: "未穿安全马甲",
  no_mask: "未戴口罩",
};

/** 违规类型下拉选项 */
export const VIOLATION_TYPE_OPTIONS = Object.entries(VIOLATION_TYPE_MAP).map(
  ([value, label]) => ({ value, label })
);

/** ppe.pt 违规类（NO-*）—— 检测框标红 */
export const NEGATIVE_CLASSES = new Set(["NO-Hardhat", "NO-Mask", "NO-Safety Vest"]);

/** ppe.pt 合规装备类 —— 检测框标绿 */
export const POSITIVE_CLASSES = new Set(["Hardhat", "Mask", "Safety Vest"]);

/** 检测目标 -> 标签颜色（与后端 annotate.py / 原始脚本配色一致） */
export function classColor(clsName: string): string {
  if (NEGATIVE_CLASSES.has(clsName)) return "#f56c6c"; // 红：违规
  if (POSITIVE_CLASSES.has(clsName)) return "#67c23a"; // 绿：合规装备
  return "#409eff"; // 蓝：其他目标
}
