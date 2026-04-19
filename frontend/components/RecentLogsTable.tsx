'use client'

import clsx from 'clsx'
import type { LogSummary } from '@/lib/types'
import { StatusBadge } from './StatusBadge'
import { formatTime, rowBg } from '@/lib/utils'

interface Props {
  logs: LogSummary[]
  onRowClick: (log: LogSummary) => void
  onRetry: (id: string) => void
  retryingIds: Set<string>
}

export function RecentLogsTable({ logs, onRowClick, onRetry, retryingIds }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr>
            {['Time', 'Target System', 'Protocol', 'API / Job Name', 'Status', ''].map(h => (
              <th
                key={h}
                className="px-3 py-2 text-left text-[10px] font-semibold tracking-[0.07em] uppercase whitespace-nowrap border-b border-border"
                style={{ color: 'var(--dim)', background: 'oklch(0.15 0.008 75)' }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map(log => {
            const bg = rowBg(log.status)
            return (
              <tr
                key={log.id}
                onClick={() => onRowClick(log)}
                className={clsx('cursor-pointer transition-colors', bg)}
                style={{ borderBottom: '1px solid oklch(0.19 0.006 75)' }}
              >
                <td
                  className="px-3 py-[9px] font-mono text-[11px]"
                  style={{ color: 'var(--dim)' }}
                >
                  {formatTime(log.called_at)}
                </td>
                <td className="px-3 py-[9px]" style={{ color: 'var(--text)' }}>
                  {log.target_org}
                </td>
                <td className="px-3 py-[9px] font-mono text-[12px]" style={{ color: 'var(--muted)' }}>
                  {log.protocol}
                </td>
                <td className="px-3 py-[9px] font-mono text-[12px]" style={{ color: 'var(--muted)' }}>
                  {log.service_name}
                </td>
                <td className="px-3 py-[9px]">
                  <StatusBadge status={log.status} />
                </td>
                <td className="px-3 py-[9px] text-right">
                  {(log.status === 'FAILED' || log.status === 'PENDING') && log.retry_count < 3 && (
                    <button
                      onClick={e => { e.stopPropagation(); onRetry(log.id) }}
                      disabled={retryingIds.has(log.id)}
                      className="px-[8px] py-[4px] text-[11px] font-medium rounded-[2px] cursor-pointer transition-colors disabled:opacity-50"
                      style={{
                        background: 'var(--danger-dim)',
                        color:      'var(--danger)',
                        border:     '1px solid oklch(0.65 0.18 28 / 0.25)',
                      }}
                    >
                      {retryingIds.has(log.id) ? '처리 중…' : '↺ Retry'}
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
