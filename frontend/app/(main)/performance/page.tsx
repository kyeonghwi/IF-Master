'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { PerformanceResponse } from '@/lib/types'
import { authFetch } from '@/lib/api'
import { Topbar } from '@/components/Topbar'
import { ProtocolBadge } from '@/components/ProtocolBadge'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

const SLA_MS = 3000

function fmt(ms: number) {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.round(ms)}ms`
}

export default function PerformancePage() {
  const [range, setRange] = useState('24h')

  const hoursMap: Record<string, number> = { '1h': 1, '6h': 6, '24h': 24, '7d': 168 }
  const hours = hoursMap[range] ?? 24
  const to = new Date()
  const from = new Date(to.getTime() - hours * 3600 * 1000)

  const { data, isLoading, isError, refetch } = useQuery<PerformanceResponse>({
    queryKey: ['performance', range],
    queryFn: () => authFetch<PerformanceResponse>(
      `/api/performance?from_dt=${from.toISOString()}&to_dt=${to.toISOString()}`
    ),
    staleTime: 60_000,
  })

  const sla = data?.sla_summary
  const byIf = data?.by_interface ?? []
  const alerts = data?.slow_alerts ?? []

  const avgMs = byIf.length > 0
    ? byIf.reduce((a, r) => a + r.avg_ms * r.call_count, 0) / byIf.reduce((a, r) => a + r.call_count, 0)
    : 0
  const p95Max = byIf.length > 0 ? Math.max(...byIf.map(r => r.p95_ms)) : 0

  const chartData = byIf.slice(0, 15).map(r => ({
    name: r.service_name.length > 14 ? r.service_name.slice(0, 14) + '…' : r.service_name,
    p95: Math.round(r.p95_ms),
    protocol: r.protocol,
  }))

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="성능 관리" subtitle="Performance" />

      <div className="flex-1 px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-[18px] font-semibold text-text">성능 관리</h1>
            <p className="text-[12px] text-muted mt-[3px]">인터페이스별 응답시간 및 SLA 준수율 모니터링</p>
          </div>
          <div className="flex gap-1">
            {['1h', '6h', '24h', '7d'].map(r => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-[5px] text-[11px] rounded border transition-colors ${
                  range === r
                    ? 'border-accent/40 bg-accent/10 text-accent'
                    : 'border-border text-muted hover:text-text'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            {/* Slow alerts — above KPIs */}
            {alerts.length > 0 && (
              <div className="mb-4 rounded-md border border-warning/30 bg-warning/5 px-4 py-3">
                <p className="text-[12px] font-medium text-warning mb-1">⚠ 느린 인터페이스 알림 (P95 &gt; {SLA_MS.toLocaleString()}ms)</p>
                <div className="flex flex-wrap gap-3">
                  {alerts.map(a => (
                    <span key={a.service_name} className="text-[12px] text-warning/80">
                      {a.service_name}: P95 {fmt(a.p95_ms)} · {a.call_count.toLocaleString()}건
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* KPI cards */}
            <div className="grid grid-cols-4 gap-3 mb-6">
              <KpiCard
                label="SLA 준수율"
                tooltip={`SLA 목표: 99% (${SLA_MS.toLocaleString()}ms 이하)`}
                value={sla ? `${sla.sla_rate.toFixed(1)}%` : '-'}
                sub={sla ? `${sla.within_sla.toLocaleString()} / ${sla.total_calls.toLocaleString()}건` : ''}
                accent={sla && sla.sla_rate < 99 ? 'warning' : 'success'}
              />
              <KpiCard
                label="평균 응답시간"
                tooltip="전체 인터페이스 가중 평균"
                value={avgMs ? fmt(avgMs) : '-'}
                sub="weighted avg"
              />
              <KpiCard
                label="최대 P95"
                tooltip="P95: 전체 호출의 95%가 이 시간 내 완료"
                value={p95Max ? fmt(p95Max) : '-'}
                sub="worst interface"
                accent={p95Max > SLA_MS ? 'warning' : undefined}
              />
              <KpiCard
                label="지연 알림"
                tooltip={`P95 > ${SLA_MS.toLocaleString()}ms 인터페이스 수`}
                value={String(alerts.length)}
                sub="interfaces"
                accent={alerts.length > 0 ? 'danger' : undefined}
              />
            </div>

            {/* P95 chart */}
            {chartData.length > 0 ? (
              <div className="rounded-md border border-border p-4 mb-4">
                <p className="text-[12px] font-medium text-muted mb-4">인터페이스별 P95 응답시간</p>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 32 }}>
                    <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickFormatter={v => `${v}ms`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--muted)' }} width={130} />
                    <Tooltip
                      formatter={(v: number) => [fmt(v), 'P95']}
                      contentStyle={{ background: 'oklch(0.18 0.008 75)', border: '1px solid var(--border)', fontSize: 12 }}
                      labelStyle={{ color: 'var(--text)' }}
                    />
                    <ReferenceLine x={SLA_MS} stroke="var(--warning)" strokeDasharray="4 3" label={{ value: 'SLA 3s', position: 'insideTopRight', fontSize: 10, fill: 'var(--warning)' }} />
                    <Bar dataKey="p95" radius={[0, 3, 3, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={entry.p95 > SLA_MS ? 'var(--danger)' : 'var(--accent)'} fillOpacity={0.7} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyChart />
            )}

            {/* Detail table */}
            {byIf.length > 0 && (
              <div className="rounded-md border border-border overflow-hidden">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr style={{ background: 'oklch(0.16 0.008 75)' }} className="border-b border-border">
                      {['인터페이스명', '프로토콜', '대상기관', '호출수', '평균', 'P95', 'P99', 'SLA'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-[11px] font-medium text-muted uppercase tracking-[0.05em]">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {byIf.map((r, i) => (
                      <tr key={i} className="border-b border-border last:border-0 hover:bg-white/[0.02]">
                        <td className="px-4 py-3 text-text font-medium">{r.service_name}</td>
                        <td className="px-4 py-3"><ProtocolBadge protocol={r.protocol} /></td>
                        <td className="px-4 py-3 text-muted">{r.target_org}</td>
                        <td className="px-4 py-3 text-muted">{r.call_count.toLocaleString()}</td>
                        <td className="px-4 py-3 text-muted">{fmt(r.avg_ms)}</td>
                        <td className={`px-4 py-3 font-medium ${r.p95_ms > SLA_MS ? 'text-danger' : 'text-text'}`}>{fmt(r.p95_ms)}</td>
                        <td className="px-4 py-3 text-muted">{fmt(r.p99_ms)}</td>
                        <td className={`px-4 py-3 font-medium ${r.sla_rate < 99 ? 'text-warning' : 'text-success'}`}>
                          {r.sla_rate.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function KpiCard({ label, tooltip, value, sub, accent }: {
  label: string; tooltip: string; value: string; sub: string; accent?: 'success' | 'warning' | 'danger'
}) {
  const colorCls = accent === 'danger' ? 'text-danger' : accent === 'warning' ? 'text-warning' : accent === 'success' ? 'text-success' : 'text-text'
  return (
    <div className="rounded-md border border-border p-4" style={{ background: 'oklch(0.16 0.008 75)' }}>
      <div className="flex items-center gap-1 mb-2">
        <p className="text-[11px] text-muted uppercase tracking-[0.05em]">{label}</p>
        <span title={tooltip} className="text-[10px] text-dim cursor-help">ⓘ</span>
      </div>
      <p className={`text-[22px] font-bold ${colorCls}`}>{value}</p>
      <p className="text-[11px] text-dim mt-1">{sub}</p>
    </div>
  )
}

function EmptyChart() {
  return (
    <div className="rounded-md border border-border p-8 mb-4 flex items-center justify-center">
      <p className="text-[13px] text-muted">해당 기간에 데이터가 없습니다</p>
    </div>
  )
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-md border border-danger/30 bg-danger/5 p-8 flex flex-col items-center gap-3">
      <p className="text-[13px] text-danger">데이터 로드 실패</p>
      <button onClick={onRetry} className="px-3 py-[5px] text-[12px] rounded border border-danger/30 text-danger hover:bg-danger/10 transition-colors">
        재시도
      </button>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-md border border-border bg-white/5 animate-pulse" />
        ))}
      </div>
      <div className="h-72 rounded-md border border-border bg-white/5 animate-pulse" />
    </div>
  )
}
