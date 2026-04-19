'use client'

import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table'
import clsx from 'clsx'
import type { LogSummary } from '@/lib/types'
import { formatDateTime, formatLatency, rowBg } from '@/lib/utils'

const col = createColumnHelper<LogSummary>()

interface Props {
  logs: LogSummary[]
  page: number
  pageSize: number
  onRowClick: (log: LogSummary) => void
}

export function LogTable({ logs, page, pageSize, onRowClick }: Props) {
  const offset = (page - 1) * pageSize

  const columns = [
    col.display({
      id: 'num',
      header: '#',
      cell: info => (
        <span className="font-mono text-[11px]" style={{ color: 'var(--dim)' }}>
          {String(offset + info.row.index + 1).padStart(3, '0')}
        </span>
      ),
      size: 40,
    }),
    col.accessor('called_at', {
      header: 'Timestamp',
      cell: info => (
        <span className="font-mono text-[11px]" style={{ color: 'var(--muted)' }}>
          {formatDateTime(info.getValue())}
        </span>
      ),
      size: 160,
    }),
    col.accessor('status', {
      header: 'Level',
      cell: info => {
        const s = info.getValue()
        const label =
          s === 'FAILED'  ? 'Critical' :
          s === 'PENDING' ? 'Warning'  : 'Info'
        const color =
          s === 'FAILED'  ? 'var(--danger)'  :
          s === 'PENDING' ? 'var(--warning)' : 'var(--success)'
        return (
          <span
            className="text-[10px] font-bold tracking-[0.06em] uppercase"
            style={{ color }}
          >
            {label}
          </span>
        )
      },
      size: 72,
    }),
    col.accessor('target_org', {
      header: 'Node',
      cell: info => <span style={{ color: 'var(--text)' }}>{info.getValue()}</span>,
      size: 130,
    }),
    col.accessor('service_name', {
      header: 'Endpoint / Job',
      cell: info => (
        <span className="font-mono text-[12px]" style={{ color: 'var(--muted)' }}>
          {info.getValue()}
        </span>
      ),
    }),
    col.display({
      id: 'latency',
      header: 'Latency',
      cell: info => {
        const row = info.row.original
        const lat = formatLatency(row.called_at, row.responded_at)
        const color =
          lat.variant === 'danger'  ? 'var(--danger)'  :
          lat.variant === 'warning' ? 'var(--warning)' : 'var(--dim)'
        return (
          <span className="font-mono text-[11px]" style={{ color }}>
            {lat.text}
          </span>
        )
      },
      size: 80,
    }),
    col.accessor('error_message', {
      header: 'Message',
      cell: info => (
        <span
          className="text-[12px] block overflow-hidden text-ellipsis whitespace-nowrap"
          style={{ color: 'var(--muted)', maxWidth: 300 }}
        >
          {info.getValue() ?? '—'}
        </span>
      ),
      size: 300,
    }),
    col.display({
      id: 'action',
      header: '',
      cell: info => (
        <button
          onClick={e => { e.stopPropagation(); onRowClick(info.row.original) }}
          className="px-2 py-[3px] text-[11px] font-medium cursor-pointer transition-colors rounded-[2px]"
          style={{
            background: 'transparent',
            color:      'var(--dim)',
            border:     '1px solid var(--border)',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          View
        </button>
      ),
      size: 60,
    }),
  ]

  const table = useReactTable({
    data: logs,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              {hg.headers.map(header => (
                <th
                  key={header.id}
                  className="px-3 py-2 text-left text-[10px] font-semibold tracking-[0.07em] uppercase whitespace-nowrap border-b border-border"
                  style={{
                    color:      'var(--dim)',
                    background: 'oklch(0.15 0.008 75)',
                    width:      header.getSize(),
                  }}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map(row => {
            const bg = rowBg(row.original.status)
            return (
              <tr
                key={row.id}
                onClick={() => onRowClick(row.original)}
                className={clsx('cursor-pointer transition-colors', bg)}
                style={{ borderBottom: '1px solid oklch(0.19 0.006 75)' }}
              >
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-3 py-[9px] align-middle">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
