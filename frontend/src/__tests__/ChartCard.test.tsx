import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ChartSpec } from '../api/types'

vi.mock('echarts-for-react/esm/core', () => ({
  default: ({ option }: { option: Record<string, unknown> }) => (
    <div data-testid="echart" data-option={JSON.stringify(option)} />
  ),
}))

vi.mock('echarts/core', () => ({ default: {}, use: vi.fn() }))
vi.mock('echarts/charts', () => ({
  BarChart: {},
  LineChart: {},
  PieChart: {},
  ScatterChart: {},
}))
vi.mock('echarts/components', () => ({
  DatasetComponent: {},
  GridComponent: {},
  LegendComponent: {},
  TitleComponent: {},
  TooltipComponent: {},
}))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))

import ChartCard from '../components/ChartCard'

describe('ChartCard', () => {
  it('normalizes legacy chart payloads into echarts options', () => {
    document.documentElement.style.setProperty('--text-main', '#111111')
    document.documentElement.style.setProperty('--text-muted', '#777777')
    document.documentElement.style.setProperty('--border-color', '#dddddd')

    render(
      <ChartCard
        spec={{
          type: 'line',
          title: 'Revenue trend',
          xKey: 'month',
          series: [{ key: 'revenue', name: 'Revenue' }],
          data: [{ month: 'Jan', revenue: 10 }],
        }}
      />,
    )

    expect(screen.getByText('Revenue trend')).toBeInTheDocument()
    expect(screen.getByText('Converted from legacy chart payload.')).toBeInTheDocument()

    const option = JSON.parse(screen.getByTestId('echart').getAttribute('data-option') ?? '{}')
    expect(option.legend.textStyle.color).toBe('#777777')
    expect(option.xAxis.axisLine.lineStyle.color).toBe('#dddddd')
  })

  it('preserves v2 pie chart options and renders truncation warnings', () => {
    const spec: ChartSpec = {
      version: '2.0',
      engine: 'echarts',
      kind: 'pie',
      title: 'Share',
      description: 'Distribution',
      dataset: [],
      option: {
        legend: { orient: 'vertical' },
        series: [{ type: 'pie' }],
      },
      meta: {
        row_count: 100,
        truncated: true,
        warnings: ['Input rows were sampled.'],
        source_columns: ['category', 'value'],
      },
    }

    render(<ChartCard spec={spec} />)

    expect(screen.getByText('Distribution')).toBeInTheDocument()
    expect(screen.getByText('Showing a truncated view of the dataset for readability.')).toBeInTheDocument()
    expect(screen.getByText('Input rows were sampled.')).toBeInTheDocument()

    const option = JSON.parse(screen.getByTestId('echart').getAttribute('data-option') ?? '{}')
    expect(option.legend.orient).toBe('vertical')
    expect(option.xAxis).toBeUndefined()
  })
})
