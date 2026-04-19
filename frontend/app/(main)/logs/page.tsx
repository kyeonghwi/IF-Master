'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { LogsResponse, LogDetail, LogSummary } from '@/lib/types'
import { authFetch, ApiError } from '@/lib/api'
import { useSSE } from '@/hooks/useSSE'
import { Topbar } from '@/components/Topbar'
import { FilterBar, type LogFilters } from '@/components/FilterBar'
import { LogTable } from '@/components/LogTable'
import { SlidePanel } from '@/components/SlidePanel'

const PAGE_SIZE = 50

export default function LogsPage() {
  const queryClient = useQueryClient()
  const [connected,   setConnected]   = useState(false)
  const [page,        setPage]        = useState(1)
  const [filters,     setFilters]     = useState<LogFilters>({ status: '', target_org: '' })
  const [selectedLog, setSelectedLog] = useState<LogDetail | null>(null)
  const [panelOpen,   setPanelOpen]   = useState(false)
  const [retrying,    setRetrying]    = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'danger' | 'warning' } | null>(null)

  function showToast(msg: string, type: 'success' | 'danger' | 'warning') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 5000)
  }

  const logsQuery = useQuery<LogsResponse>({
    queryKey: ['logs', page, filters],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), size: String(PAGE_SIZE) })
      if (filters.status)     params.set('status', filters.status)
      if (filters.target_org) params.set('target_org', filters.target_org)
      return authFetch<LogsResponse>(`/api/logs?${params}`)
    },
    staleTime: 20_000,
  })

  useSSE({
    onConnected:    () => setConnected(true),
    onDisconnected: () => setConnected(false),
    onTransaction:  () => queryClient.invalidateQueries({ queryKey: ['logs'] }),
    onRetryResult:  (evt) => {
      queryClient.invalidateQueries({ queryKey: ['logs'] })
      const ok = evt.result === 'SUCCESS' || evt.result === 'ALREADY_PROCESSED'
      showToast(evt.message, ok ? 'success' : 'danger')
    },
  })

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
    setRetrying(true)
    try {
      const result = await authFetch<{ result: string; message: string }>(`/api/retry/${id}`, { method: 'POST' })
      const ok = result.result === 'SUCCESS' || result.result === 'ALREADY_PROCESSED'
      showToast(result.message, ok ? 'success' : 'danger')
      queryClient.invalidateQueries({ queryKey: ['logs'] })
      if (panelOpen && selectedLog?.id === id) {
        const detail = await authFetch<LogDetail>(`/api/logs/${id}`)
        setSelectedLog(detail)
      }
    } catch (err) {
      const codeMessages: Record<string, string> = {
        NOT_RETRYABLE:        '재처리 불가 상태',
        RETRY_LIMIT_EXCEEDED: '최대 재처리 횟수 초과 (3회)',
      }
      const msg =
        err instanceof ApiError && err.code && codeMessages[err.code]
          ? codeMessages[err.code]
          : err instanceof ApiError
            ? err.message
            : '재처리 실패'
      showToast(msg, 'warning')
    } finally {
      setRetrying(false)
    }
  }

  function handleApplyFilters(f: LogFilters) {
    setFilters(f)
    setPage(1)
  }

  function handleResetFilters() {
    setFilters({ status: '', target_org: '' })
    setPage(1)
  }

  const total      = logsQuery.data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1
  const logs       = logsQuery.data?.items ?? []
  const from       = total === 0 ? 0 : Math.min((page - 1) * PAGE_SIZE + 1, total)
  const to         = Math.min(page * PAGE_SIZE, total)

  // Active filter chips
  const chips: Array<{ key: string; label: string; onRemove: () => void }> = []
  if (filters.status) chips.push({
    key:      'level',
    label:    `Level: ${filters.status === 'FAILED' ? 'Critical' : filters.status === 'PENDING' ? 'Warning' : 'Info'}`,
    onRemove: () => handleApplyFilters({ ...filters, status: '' }),
  })
  if (filters.target_org) chips.push({
    key:      'system',
    label:    `System: ${filters.target_org}`,
    onRemove: () => handleApplyFilters({ ...filters, target_org: '' }),
  })

  // Page number window: up to 5 pages centered around current
  const windowStart = Math.max(1, Math.min(page - 2, totalPages - 4))
  const pageNumbers = Array.from(
    { length: Math.min(5, totalPages) },
    (_, i) => windowStart + i,
  ).filter(p => p <= totalPages)

  return (
    <>
      <Topbar
        title="Interface Logs"
        subtitle="인터페이스 호출 이력 전체 조회"
        connected={connected}
      >
        <span className="font-mono text-[12px]" style={{ color: 'var(--dim)' }}>
          Showing {from}–{to} of {total.toLocaleString('ko-KR')}
        </span>
      </Topbar>

      <FilterBar
        filters={filters}
        onApply={handleApplyFilters}
        onReset={handleResetFilters}
      />

      {/* Active filter chips */}
      {chips.length > 0 && (
        <div
          className="flex flex-wrap items-center gap-[6px] px-6 py-[6px] border-b border-border shrink-0"
          style={{ minHeight: 34 }}
        >
          {chips.map(chip => (
            <span
              key={chip.key}
              className="flex items-center gap-[4px] px-[8px] py-[3px] text-[11px] rounded-[2px] border border-border"
              style={{ background: 'var(--surface-2)', color: 'var(--muted)' }}
            >
              {chip.label}
              <button
                onClick={chip.onRemove}
                style={{
                  background: 'none',
                  border:     'none',
                  color:      'var(--dim)',
                  cursor:     'pointer',
                  padding:    0,
                  marginLeft: 2,
                  fontSize:   13,
                  lineHeight: 1,
                }}
              >
                &times;
              </button>
            </span>
          ))}
          <button
            onClick={handleResetFilters}
            className="text-[11px]"
            style={{
              background: 'none',
              border:     'none',
              color:      'var(--accent-text)',
              cursor:     'pointer',
              marginLeft: 4,
            }}
          >
            Clear All
          </button>
        </div>
      )}

      {/* Table + Pagination */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          {logsQuery.isLoading ? (
            <div className="p-8 text-center text-[12px]" style={{ color: 'var(--dim)' }}>
              로그 불러오는 중…
            </div>
          ) : logsQuery.isError ? (
            <div className="p-8 text-center text-[12px]" style={{ color: 'var(--danger)' }}>
              데이터를 불러오지 못했습니다.
              {logsQuery.error instanceof Error && (
                <div className="mt-1 text-[11px]" style={{ color: 'var(--dim)' }}>
                  {logsQuery.error.message}
                </div>
              )}
            </div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-[12px]" style={{ color: 'var(--dim)' }}>
              조건에 맞는 로그가 없습니다.
            </div>
          ) : (
            <LogTable
              logs={logs}
              page={page}
              pageSize={PAGE_SIZE}
              onRowClick={openPanel}
            />
          )}
        </div>

        {/* Pagination */}
        <div
          className="flex items-center justify-between px-6 py-[10px] border-t border-border shrink-0"
          style={{ background: 'oklch(0.13 0.008 75)' }}
        >
          <span className="text-[12px]" style={{ color: 'var(--dim)' }}>
            Page {page} of {totalPages} &mdash; {total.toLocaleString('ko-KR')} total records
          </span>
          <div className="flex items-center gap-[4px]">
            {/* First / Prev */}
            {[
              { label: '\u00AB', disabled: page <= 1, target: 1 },
              { label: '\u2039', disabled: page <= 1, target: page - 1 },
            ].map(({ label, disabled, target }) => (
              <button
                key={label}
                disabled={disabled}
                onClick={() => setPage(target)}
                className="px-[8px] py-[4px] text-[12px] rounded-[2px] border border-border cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                style={{ background: 'transparent', color: 'var(--muted)' }}
                onMouseEnter={e => { if (!disabled) e.currentTarget.style.background = 'var(--surface-2)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
              >
                {label}
              </button>
            ))}

            {/* Page number buttons */}
            {pageNumbers.map(p => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className="px-[8px] py-[4px] text-[12px] rounded-[2px] border cursor-pointer transition-colors"
                style={{
                  background:  p === page ? 'var(--accent-dim)' : 'transparent',
                  color:       p === page ? 'var(--accent-text)' : 'var(--muted)',
                  borderColor: p === page ? 'oklch(0.78 0.14 82 / 0.25)' : 'var(--border)',
                }}
              >
                {p}
              </button>
            ))}

            {/* Next / Last */}
            {[
              { label: '\u203A', disabled: page >= totalPages, target: page + 1 },
              { label: '\u00BB', disabled: page >= totalPages, target: totalPages },
            ].map(({ label, disabled, target }) => (
              <button
                key={label}
                disabled={disabled}
                onClick={() => setPage(target)}
                className="px-[8px] py-[4px] text-[12px] rounded-[2px] border border-border cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                style={{ background: 'transparent', color: 'var(--muted)' }}
                onMouseEnter={e => { if (!disabled) e.currentTarget.style.background = 'var(--surface-2)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className="fixed bottom-5 right-5 z-[9999] flex items-center gap-3 px-4 py-[10px] text-[12px] font-medium border"
          style={{
            background:   toast.type === 'success' ? 'var(--success-dim)' :
                          toast.type === 'danger'  ? 'var(--danger-dim)'  : 'var(--warning-dim)',
            color:        toast.type === 'success' ? 'var(--success)' :
                          toast.type === 'danger'  ? 'var(--danger)'  : 'var(--warning)',
            borderColor:  toast.type === 'success' ? 'oklch(0.70 0.12 160 / .30)' :
                          toast.type === 'danger'  ? 'oklch(0.65 0.18 28 / .30)'  : 'oklch(0.80 0.13 70 / .30)',
            borderRadius: 2,
            minWidth:     260,
          }}
        >
          <span className="flex-1">{toast.msg}</span>
          <button
            onClick={() => setToast(null)}
            style={{
              background: 'none',
              border:     'none',
              color:      'inherit',
              opacity:    0.5,
              cursor:     'pointer',
              fontSize:   14,
              lineHeight: 1,
            }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Slide panel */}
      <SlidePanel
        log={selectedLog}
        open={panelOpen}
        onClose={() => { setPanelOpen(false); setSelectedLog(null) }}
        onRetry={handleRetry}
        retrying={retrying}
      />
    </>
  )
}
