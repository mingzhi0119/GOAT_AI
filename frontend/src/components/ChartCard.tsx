import { type FC, useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/esm/core'
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import * as echarts from 'echarts/core'
import { CHART_THEME_FALLBACK } from '../assets/uiVisualAssets'
import type { ChartSpec, ChartSpecV2, LegacyChartSpec } from '../api/types'

interface Props {
  spec: ChartSpec
}

echarts.use([
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  CanvasRenderer,
])

function isChartSpecV2(spec: ChartSpec): spec is ChartSpecV2 {
  return 'engine' in spec && spec.engine === 'echarts'
}

function legacyToEChartsSpec(spec: LegacyChartSpec): ChartSpecV2 {
  const option: Record<string, unknown> = {
    title: { text: spec.title },
    tooltip: { trigger: 'axis' },
    legend: { data: spec.series.map(series => series.name) },
    dataset: { source: spec.data },
    xAxis: { type: 'category', name: spec.xKey },
    yAxis: { type: 'value' },
    series: spec.series.map(series => ({
      type: spec.type,
      name: series.name,
      encode: { x: spec.xKey, y: series.key },
      ...(spec.type === 'line' ? { smooth: true } : {}),
    })),
  }

  return {
    version: '2.0',
    engine: 'echarts',
    kind: spec.type,
    title: spec.title,
    description: '',
    dataset: spec.data,
    option,
    meta: {
      row_count: spec.data.length,
      truncated: false,
      warnings: ['Converted from legacy chart payload.'],
      source_columns: [spec.xKey, ...spec.series.map(series => series.key)],
    },
  }
}

const ChartCard: FC<Props> = ({ spec }) => {
  const normalized = useMemo(() => (isChartSpecV2(spec) ? spec : legacyToEChartsSpec(spec)), [spec])
  const isPieChart = normalized.kind === 'pie'
  const themeColors = useMemo(() => {
    if (typeof window === 'undefined') {
      return CHART_THEME_FALLBACK
    }
    const styles = window.getComputedStyle(document.documentElement)
    return {
      text: styles.getPropertyValue('--text-main').trim() || CHART_THEME_FALLBACK.text,
      muted: styles.getPropertyValue('--text-muted').trim() || CHART_THEME_FALLBACK.muted,
      border: styles.getPropertyValue('--border-color').trim() || CHART_THEME_FALLBACK.border,
    }
  }, [])
  const option = useMemo(
    () => {
      const baseOption = {
        ...normalized.option,
        backgroundColor: 'transparent',
        textStyle: { color: themeColors.text },
        title: {
          ...(typeof normalized.option.title === 'object' && normalized.option.title !== null ? normalized.option.title : {}),
          textStyle: { color: themeColors.text },
        },
        legend: {
          ...(typeof normalized.option.legend === 'object' && normalized.option.legend !== null ? normalized.option.legend : {}),
          textStyle: { color: themeColors.muted },
        },
      }

      if (isPieChart) {
        return baseOption
      }

      return {
        ...baseOption,
        xAxis: {
          ...(typeof normalized.option.xAxis === 'object' && normalized.option.xAxis !== null ? normalized.option.xAxis : {}),
          axisLabel: { color: themeColors.muted },
          axisLine: { lineStyle: { color: themeColors.border } },
        },
        yAxis: {
          ...(typeof normalized.option.yAxis === 'object' && normalized.option.yAxis !== null ? normalized.option.yAxis : {}),
          axisLabel: { color: themeColors.muted },
          splitLine: { lineStyle: { color: themeColors.border, opacity: 0.35 } },
        },
      }
    },
    [isPieChart, normalized.option, themeColors],
  )

  return (
    <div
      className="rounded-2xl p-4 border"
      style={{ borderColor: 'var(--border-color)', background: 'var(--bg-asst-bubble)' }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-main)' }}>
            {normalized.title}
          </h3>
          {normalized.description && (
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              {normalized.description}
            </p>
          )}
        </div>
        <span
          className="text-[10px] uppercase tracking-wide px-2 py-1 rounded-full"
          style={{ color: 'var(--link-color)', background: 'var(--table-header-bg)' }}
        >
          Apache ECharts
        </span>
      </div>

      <div className="w-full h-72">
        <ReactEChartsCore
          echarts={echarts}
          option={option}
          notMerge
          lazyUpdate
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      {(normalized.meta.warnings.length > 0 || normalized.meta.truncated) && (
        <div className="mt-3 space-y-1">
          {normalized.meta.truncated && (
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Showing a truncated view of the dataset for readability.
            </p>
          )}
          {normalized.meta.warnings.map(warning => (
            <p key={warning} className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {warning}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export default ChartCard
