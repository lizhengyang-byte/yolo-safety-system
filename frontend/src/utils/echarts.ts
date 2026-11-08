/** 智慧大屏共用的 ECharts 按需注册（避免每个面板重复注册）。
 *  仅注册大屏实际用到的图表与组件，保持产物体积可控。 */
import { init, use, type ECharts } from "echarts/core";
import { LineChart, BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
  CanvasRenderer,
]);

export { init };
export type { ECharts };
