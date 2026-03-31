import { type FC } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ChartSpec } from '../api/types'

interface Props {
  spec: ChartSpec
}

const PALETTE = ['#FFCD00', '#60A5FA', '#F472B6', '#34D399']

const ChartCard: FC<Props> = ({ spec }) => {
  return (
    <div
      className="rounded-2xl p-4 border"
      style={{ borderColor: 'var(--border-color)', background: 'var(--bg-asst-bubble)' }}
    >
      <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-main)' }}>
        {spec.title}
      </h3>
      <div className="w-full h-64">
        <ResponsiveContainer>
          {spec.type === 'bar' ? (
            <BarChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={spec.xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {spec.series.map((s, idx) => (
                <Bar key={s.key} dataKey={s.key} name={s.name} fill={PALETTE[idx % PALETTE.length]} />
              ))}
            </BarChart>
          ) : (
            <LineChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={spec.xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {spec.series.map((s, idx) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.name}
                  stroke={PALETTE[idx % PALETTE.length]}
                  strokeWidth={2}
                  dot
                />
              ))}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default ChartCard
