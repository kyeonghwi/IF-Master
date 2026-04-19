'use client'

import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { SeriesPoint } from '@/lib/types'
import clsx from 'clsx'

interface Props {
  series: SeriesPoint[]
  loading?: boolean
}

type Window = '1H' | '12H' | '24H'

const WINDOWS: Window[] = ['1H', '12H', '24H']

function filterByWindow(series: SeriesPoint[], w: Window): SeriesPoint[] {
  const now = Date.now()
  const hours = w === '1H' ? 1 : w === '12H' ? 12 : 24
  const cutoff = now - hours * 3600_000
  return series.filter(p => new Date(p.timestamp).getTime() >= cutoff)
}

function formatHour(ts: string): string {
  return new Date(ts).toLocaleTimeString('ko-KR', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul',
  })
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div
      className="border border-border px-3 py-2 text-[11px]"
      style={{ background: 'var(--surface-2)', borderRadius: 2 }}
    >
      <div className="mb-1" style={{ color: 'var(--dim)' }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: {p.value}
        </div>
      ))}
    </div>
  )
}

export function TrafficChart({ series, loading }: Props) {
  const [window, setWindow] = useState<Window>('12H')
  const data = filterByWindow(series, window).map(p => ({
    time:    formatHour(p.timestamp),
    success: p.success,
    failed:  p.failed,
  }))

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="px-4 py-[11px] border-b border-border flex items-center justify-between shrink-0">
        <span
          className="font-display font-semibold text-[11px] tracking-[0.10em] uppercase"
          style={{ color: 'var(--muted)' }}
        >
          Traffic Trend — Last {window}
        </span>
        <div className="flex gap-1">
          {WINDOWS.map(w => (
            <button
              key={w}
              onClick={() => setWindow(w)}
              className={clsx(
                'px-[8px] py-[3px] text-[10px] font-semibold tracking-[0.04em] transition-colors cursor-pointer',
                'rounded-[2px] border',
              )}
              style={{
                background:  w === window ? 'var(--accent-dim)' : 'transparent',
                color:       w === window ? 'var(--accent-text)' : 'var(--dim)',
                borderColor: w === window ? 'oklch(0.78 0.14 82 / 0.25)' : 'var(--border)',
              }}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 px-4 py-3 min-h-0">
        {loading ? (
          <div className="h-full flex items-center justify-center text-[12px]" style={{ color: 'var(--dim)' }}>
            연결 중…
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-[12px]" style={{ color: 'var(--dim)' }}>
            데이터 없음
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="successGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="oklch(0.70 0.12 160)" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="oklch(0.70 0.12 160)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="failedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="oklch(0.65 0.18 28)" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="oklch(0.65 0.18 28)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="2 4"
                stroke="oklch(0.22 0.006 75)"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 9, fill: 'oklch(0.38 0.006 75)', fontFamily: 'var(--font-mono)' }}
                tickLine={false}
                axisLine={{ stroke: 'oklch(0.22 0.006 75)' }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 9, fill: 'oklch(0.38 0.006 75)', fontFamily: 'var(--font-mono)' }}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="success"
                name="Success"
                stroke="oklch(0.70 0.12 160)"
                strokeWidth={1.5}
                fill="url(#successGrad)"
                dot={false}
                activeDot={{ r: 3, fill: 'oklch(0.70 0.12 160)' }}
              />
              <Area
                type="monotone"
                dataKey="failed"
                name="Failed"
                stroke="oklch(0.65 0.18 28)"
                strokeWidth={1.5}
                fill="url(#failedGrad)"
                dot={false}
                activeDot={{ r: 3, fill: 'oklch(0.65 0.18 28)' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
