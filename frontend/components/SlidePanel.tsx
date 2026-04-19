'use client'

import clsx from 'clsx'
import type { LogDetail } from '@/lib/types'
import { StatusBadge } from './StatusBadge'
import { formatDateTime, formatLatency } from '@/lib/utils'

interface Props {
  log: LogDetail | null
  open: boolean
  onClose: () => void
  onRetry: (id: string) => void
  retrying: boolean
}

export function SlidePanel({ log, open, onClose, onRetry, retrying }: Props) {
  if (!open) return null

  const lat = log ? formatLatency(log.called_at, log.responded_at) : null
  const isRetryable = log
    ? (log.status === 'FAILED' || log.status === 'PENDING') && log.retry_count < 3
    : false

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
        style={{ background: 'oklch(0.08 0.006 75 / 0.5)' }}
      />

      {/* Panel */}
      <div
        className="fixed top-0 right-0 h-screen z-50 flex flex-col border-l border-border overflow-hidden"
        style={{ width: 420, background: 'var(--surface)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-[14px] border-b border-border shrink-0">
          <span
            className="font-display font-semibold text-[12px] tracking-[0.08em] uppercase"
            style={{ color: 'var(--muted)' }}
          >
            {log ? `Log Detail — ${log.idempotency_key}` : 'Log Detail'}
          </span>
          <button
            onClick={onClose}
            className="text-[18px] leading-none cursor-pointer transition-colors"
            style={{ color: 'var(--dim)', background: 'none', border: 'none' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--muted)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--dim)')}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
          {!log ? (
            <div className="text-[12px]" style={{ color: 'var(--dim)' }}>Loading…</div>
          ) : (
            <>
              {/* Meta rows */}
              <div className="flex flex-col gap-[6px]">
                {[
                  { k: 'Timestamp',       v: formatDateTime(log.called_at) },
                  { k: 'Target',          v: log.target_org },
                  { k: 'Protocol',        v: log.protocol },
                  { k: 'Service',         v: log.service_name },
                  { k: 'Retry Count',     v: `${log.retry_count} / 3` },
                  { k: 'Idempotency Key', v: log.idempotency_key },
                ].map(({ k, v }) => (
                  <div key={k} className="flex gap-3 text-[12px]">
                    <span
                      className="w-[120px] shrink-0 text-[10px] font-semibold uppercase tracking-[0.06em]"
                      style={{ color: 'var(--dim)', paddingTop: 1 }}
                    >
                      {k}
                    </span>
                    <span
                      className={clsx(k === 'Idempotency Key' && 'font-mono text-[11px]')}
                      style={{ color: 'var(--muted)' }}
                    >
                      {v}
                    </span>
                  </div>
                ))}

                {/* Status row with badge */}
                <div className="flex gap-3 text-[12px]">
                  <span
                    className="w-[120px] shrink-0 text-[10px] font-semibold uppercase tracking-[0.06em]"
                    style={{ color: 'var(--dim)', paddingTop: 1 }}
                  >
                    Status
                  </span>
                  <StatusBadge status={log.status} />
                </div>

                {/* Latency */}
                <div className="flex gap-3 text-[12px]">
                  <span
                    className="w-[120px] shrink-0 text-[10px] font-semibold uppercase tracking-[0.06em]"
                    style={{ color: 'var(--dim)', paddingTop: 1 }}
                  >
                    Latency
                  </span>
                  <span
                    style={{
                      color: lat?.variant === 'danger'
                        ? 'var(--danger)'
                        : lat?.variant === 'warning'
                          ? 'var(--warning)'
                          : 'var(--muted)',
                    }}
                  >
                    {lat?.text}
                  </span>
                </div>
              </div>

              {/* Request Payload */}
              {log.request_payload && (
                <div>
                  <div
                    className="text-[10px] font-semibold uppercase tracking-[0.08em] mb-2 pb-[6px] border-b border-border"
                    style={{ color: 'var(--dim)' }}
                  >
                    Request Payload
                  </div>
                  <div
                    className="font-mono text-[11px] leading-relaxed p-3 overflow-auto max-h-[200px] border border-border"
                    style={{
                      background: 'oklch(0.10 0.006 75)',
                      color: 'oklch(0.70 0.12 160)',
                      borderRadius: 2,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                    }}
                  >
                    {(() => {
                      try { return JSON.stringify(JSON.parse(log.request_payload!), null, 2) }
                      catch { return log.request_payload }
                    })()}
                  </div>
                </div>
              )}

              {/* Stack trace */}
              {log.stack_trace && (
                <div>
                  <div
                    className="text-[10px] font-semibold uppercase tracking-[0.08em] mb-2 pb-[6px] border-b border-border"
                    style={{ color: 'var(--dim)' }}
                  >
                    Error Trace
                  </div>
                  <div
                    className="font-mono text-[11px] leading-relaxed p-3 overflow-auto max-h-[180px] border border-border"
                    style={{
                      background: 'oklch(0.10 0.006 75)',
                      color: 'var(--danger)',
                      borderRadius: 2,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {log.stack_trace}
                  </div>
                </div>
              )}

              {/* Audit log */}
              {log.audit_logs.length > 0 && (
                <div>
                  <div
                    className="text-[10px] font-semibold uppercase tracking-[0.08em] mb-2 pb-[6px] border-b border-border"
                    style={{ color: 'var(--dim)' }}
                  >
                    Audit Log
                  </div>
                  <div className="flex flex-col gap-[6px]">
                    {log.audit_logs.map(a => (
                      <div key={a.id} className="flex gap-3 text-[12px]">
                        <span
                          className="text-[10px] font-semibold uppercase tracking-[0.06em] w-[120px] shrink-0"
                          style={{ color: 'var(--dim)', paddingTop: 1 }}
                        >
                          {a.action}
                        </span>
                        <span style={{ color: 'var(--muted)' }}>
                          {formatDateTime(a.executed_at).slice(11)} ·{' '}
                          <span style={{ color: 'var(--text)' }}>{a.operator}</span> · {a.result}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 py-4 border-t border-border flex gap-3 shrink-0">
          <button
            onClick={() => log && onRetry(log.id)}
            disabled={!isRetryable || retrying}
            className="px-4 py-[8px] text-[11px] font-semibold tracking-[0.04em] uppercase cursor-pointer rounded-[2px] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            title={!isRetryable ? '재처리 불가 또는 최대 3회 초과' : undefined}
            style={{
              background: 'var(--danger-dim)',
              color:      'var(--danger)',
              border:     '1px solid oklch(0.65 0.18 28 / 0.25)',
            }}
          >
            {retrying ? '처리 중…' : '↺ Retry Transaction'}
          </button>
          <button
            onClick={() => log && navigator.clipboard.writeText(log.id)}
            className="px-4 py-[8px] text-[11px] font-semibold tracking-[0.04em] uppercase cursor-pointer rounded-[2px] transition-colors"
            style={{
              background: 'transparent',
              color:      'var(--dim)',
              border:     '1px solid var(--border)',
            }}
          >
            Copy ID
          </button>
        </div>
      </div>
    </>
  )
}
