import clsx from 'clsx'
import type { StatsResponse } from '@/lib/types'
import { clampNumber, successRate } from '@/lib/utils'

interface Props {
  stats: StatsResponse | undefined
  loading?: boolean
}

interface Cell {
  label: string
  getValue: (s: StatsResponse) => React.ReactNode
  valueClass: string
  delta: string
}

const CELLS: Cell[] = [
  {
    label: 'Total Transactions',
    getValue: s => clampNumber(s.total),
    valueClass: 'text-accent',
    delta: '오늘 기준',
  },
  {
    label: 'Success Rate',
    getValue: s => successRate(s.success, s.total),
    valueClass: 'text-success',
    delta: '최근 24h',
  },
  {
    label: 'Failed Transactions',
    getValue: s => clampNumber(s.failed),
    valueClass: 'text-danger',
    delta: '즉시 확인 필요',
  },
  {
    label: 'Pending',
    getValue: s => clampNumber(s.pending),
    valueClass: 'text-warning',
    delta: '처리 대기 중',
  },
]

export function StatsRow({ stats, loading }: Props) {
  return (
    <div className="flex border border-border rounded-[2px] overflow-hidden">
      {CELLS.map((cell, i) => (
        <div
          key={cell.label}
          className={clsx(
            'flex-1 px-5 py-[14px] bg-surface',
            i < CELLS.length - 1 && 'border-r border-border',
          )}
        >
          <div
            className="text-[10px] font-semibold tracking-[0.08em] uppercase mb-[5px]"
            style={{ color: 'var(--dim)' }}
          >
            {cell.label}
          </div>
          <div
            className={clsx(
              'font-display font-bold text-[26px] leading-none',
              cell.valueClass,
              loading && 'opacity-40',
            )}
          >
            {stats ? cell.getValue(stats) : '—'}
          </div>
          <div className="text-[11px] mt-[3px]" style={{ color: 'var(--dim)' }}>
            {cell.delta}
          </div>
        </div>
      ))}
    </div>
  )
}
