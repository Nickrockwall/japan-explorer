// 本站用到的 ECharts 部件（按需打包，见 tools/echarts/build.sh）。用到新的图表类型 / 组件时在这里加上再重建。
import * as echarts from 'echarts/core';
import { MapChart, ScatterChart, EffectScatterChart, LinesChart, CustomChart } from 'echarts/charts';
import { GeoComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([MapChart, ScatterChart, EffectScatterChart, LinesChart, CustomChart, GeoComponent, TooltipComponent, CanvasRenderer]);
export * from 'echarts/core';
