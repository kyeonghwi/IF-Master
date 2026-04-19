'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { StatsResponse, LogsResponse, LogDetail, LogSummary } from '@/lib/types'
import { authFetch, ApiError } from '@/lib/api'
import { useSSE } from '@/hooks/useSSE'
import { Topbar } from '@/components/Topbar'
import { StatsRow } from '@/components/StatsRow'
import { TrafficChart } from '@/components/TrafficChart'
import { RecentLogsTable } from '@/components/RecentLogsTable'
import { SlidePanel } from '@/components/SlidePanel'

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const [connected,     setConnected]     = useState(false)
  const [selectedLog,   setSelectedLog]   = useState<LogDetail | null>(null)
  const [panelOpen,     setPanelOpen]     = useState(false)
  const [retryingIds,   setRetryingIds]   = useState<Set<string>>(new Set())
  const [retryingPanel, setRetryingPanel] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'danger' | 'warning' } | null>(null)

  // Stats query (refetch every 30s)
  const statsQuery = useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn:  () => authFetch<StatsResponse>('/api/stats'),
    staleTime: 30_000,
  })

  // Recent logs query
  const logsQuery = useQuery<LogsResponse>({
    queryKey: ['recent-logs'],
    queryFn:  () => authFetch<LogsResponse>('/api/logs?size=10'),
    staleTime: 20_000,
  })

  // SSE: invalidate queries on new transaction
  useSSE({
    onConnected:    () => setConnected(true),
    onDisconnected: () => setConnected(false),
    onTransaction: () => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['recent-logs'] })
    },
    onRetryResult: (evt) => {
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['recent-logs'] })
      showToast(
        evt.message,
        evt.result === 'SUCCESS' || evt.result === 'ALREADY_PROCESSED' ? 'success' : 'danger',
      )
    },
  })

  function showToast(msg: string, type: 'success' | 'danger' | 'warning') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 5000)
  }

  async function openPanel(log: LogSummary) {
    setPanelOpen(true)
    setSelectedLog(null)
    try {
      const detail = await authFetch<LogDetail>(`/api/logs/${log.id}`)
      setSelectedLog(detail)
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : '상세 조회 실패', 'danger')
      setPanelOpen(false)
    }
  }

  async function handleRetry(id: string) {
    setRetryingIds(prev => new Set(prev).add(id))
    setRetryingPanel(true)
    try {
      const result = await authFetch<{ result: string; message: string }>(`/api/retry/${id}`, { method: 'POST' })
      const ok = result.result === 'SUCCESS' || result.result === 'ALREADY_PROCESSED'
      showToast(result.message, ok ? 'success' : 'danger')
      queryClient.invalidateQueries({ queryKey: ['recent-logs'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      if (panelOpen && selectedLog?.id === id) {
        const detail = await authFetch<LogDetail>(`/api/logs/${id}`)
        setSelectedLog(detail)
      }
    } catch (err) {
      const msg = err instanceof ApiError && err.code
        ? ({ NOT_RETRYABLE: '재처리 불가 상태', RETRY_LIMIT_EXCEEDED: '최대 재처리 횟수 초과 (3회)' }[err.code] ?? err.message)
        : '재처리 실패'
      showToast(msg, 'warning')
    } finally {
      setRetryingIds(prev => { const s = new Set(prev); s.delete(id); return s })
      setRetryingPanel(false)
    }
  }

  const logs = logsQuery.data?.items ?? []

  return (
    <>
      <Topbar
        title="Sentinel Lens"
        subtitle="실시간 인터페이스 통합 관제"
        connected={connected}
      />

      <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-5">

        {/* Stats */}
        <StatsRow stats={statsQuery.data} loading={statsQuery.isLoading} />

        {/* Chart + Error Distribution grid */}
        <div className="grid gap-4" style={{ gridTemplateColumns: '3fr 2fr' }}>

          {/* Traffic chart */}
          <div className="border border-border rounded-[2px] bg-surface" style={{ minHeight: 220 }}>
            <TrafficChart
              series={statsQuery.data?.series ?? []}
              loading={statsQuery.isLoading}
            />
          </div>

          {/* Error distribution */}
          <div className="border border-border rounded-[2px] bg-surface">
            <div className="px-4 py-[11px] border-b border-border">
              <span
                className="font-display font-semibold text-[11px] tracking-[0.10em] uppercase"
                style={{ color: 'var(--muted)' }}
              >
                Error Distribution
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr>
                    {['System', 'Protocol', 'Error Type', 'Count'].map(h => (
                      <th
                        key={h}
                        className="px-3 py-2 text-left text-[10px] font-semibold tracking-[0.07em] uppercase border-b border-border"
                        style={{ color: 'var(--dim)', background: 'oklch(0.15 0.008 75)' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(logsQuery.data?.items ?? [])
                    .filter(l => l.status === 'FAILED')
                    .slice(0, 5)
                    .map(l => (
                      <tr
                        key={l.id}
                        style={{
                          background: 'var(--danger-dim)',
                          borderBottom: '1px solid oklch(0.19 0.006 75)',
                        }}
                      >
                        <td className="px-3 py-[9px]" style={{ color: 'var(--text)' }}>
                          {l.target_org}
                        </td>
                        <td className="px-3 py-[9px] font-mono text-[12px]" style={{ color: 'var(--muted)' }}>
                          {l.protocol}
                        </td>
                        <td className="px-3 py-[9px]" style={{ color: 'var(--muted)' }}>
                          {l.error_message?.split(':')[0] ?? 'Error'}
                        </td>
                        <td className="px-3 py-[9px] text-right" style={{ color: 'var(--danger)' }}>
                          1
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              <div className="px-3 py-2 text-[11px]" style={{ color: 'var(--dim)' }}>
                데이터 기준: 최근 조회
              </div>
            </div>
          </div>
        </div>

        {/* Recent logs */}
        <div className="border border-border rounded-[2px] bg-surface">
          <div className="px-4 py-[11px] border-b border-border flex items-center justify-between">
            <span
              className="font-display font-semibold text-[11px] tracking-[0.10em] uppercase"
              style={{ color: 'var(--muted)' }}
            >
              Recent Interface Logs
            </span>
            <a
              href="/logs"
              className="text-[12px] no-underline transition-colors"
              style={{ color: 'var(--muted)' }}
            >
              View Full Logs →
            </a>
          </div>
          <RecentLogsTable
            logs={logs}
            onRowClick={openPanel}
            onRetry={handleRetry}
            retryingIds={retryingIds}
          />
        </div>

      </div>

      {/* Toast */}
      {toast && (
        <div
          className="fixed bottom-5 right-5 z-[9999] flex items-center gap-3 px-4 py-3 text-[12px] border"
          style={{
            background: toast.type === 'success'
              ? 'var(--success-dim)'
              : toast.type === 'danger'
                ? 'var(--danger-dim)'
                : 'var(--warning-dim)',
            color: toast.type === 'success'
              ? 'var(--success)'
              : toast.type === 'danger'
                ? 'var(--danger)'
                : 'var(--warning)',
            borderColor: toast.type === 'success'
              ? 'oklch(0.70 0.12 160 / .25)'
              : toast.type === 'danger'
                ? 'oklch(0.65 0.18 28 / .25)'
                : 'oklch(0.80 0.13 70 / .25)',
            borderRadius: 2,
            minWidth: 260,
            maxWidth: 400,
          }}
        >
          <span className="flex-1">{toast.msg}</span>
          <button
            onClick={() => setToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'inherit',
              opacity: 0.5,
              cursor: 'pointer',
              fontSize: 14,
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Slide panel */}
      <SlidePanel
        log={selectedLog}
        open={panelOpen}
        onClose={() => { setPanelOpen(false); setSelectedLog(null) }}
        onRetry={handleRetry}
        retrying={retryingPanel}
      />
    </>
  )
}
