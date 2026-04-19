'use client'

import { useState, useEffect } from 'react'

export interface LogFilters {
  status: string
  target_org: string
}

interface Props {
  filters: LogFilters
  onApply: (filters: LogFilters) => void
  onReset: () => void
}

const TARGET_ORGS = ['All', '금감원', 'KB은행', '현대카드', 'KCB', '삼성화재']
const LEVELS = [
  { label: 'All Events', value: '' },
  { label: 'Critical',   value: 'FAILED' },
  { label: 'Warning',    value: 'PENDING' },
  { label: 'Info',       value: 'SUCCESS' },
]

const selectStyle: React.CSSProperties = {
  background:   'var(--surface)',
  border:       '1px solid var(--border)',
  color:        'var(--muted)',
  fontSize:     12,
  padding:      '5px 8px',
  borderRadius: 2,
  cursor:       'pointer',
  outline:      'none',
  fontFamily:   'var(--font-sans)',
  minWidth:     130,
}

const btnBase: React.CSSProperties = {
  display:      'inline-flex',
  alignItems:   'center',
  fontSize:     11,
  fontWeight:   500,
  padding:      '5px 10px',
  borderRadius: 2,
  cursor:       'pointer',
  fontFamily:   'var(--font-sans)',
}

export function FilterBar({ filters, onApply, onReset }: Props) {
  const [localStatus,    setLocalStatus]    = useState(filters.status)
  const [localTargetOrg, setLocalTargetOrg] = useState(filters.target_org || 'All')

  // Sync when parent resets
  useEffect(() => { setLocalStatus(filters.status) },           [filters.status])
  useEffect(() => { setLocalTargetOrg(filters.target_org || 'All') }, [filters.target_org])

  function handleApply() {
    onApply({
      status:     localStatus,
      target_org: localTargetOrg === 'All' ? '' : localTargetOrg,
    })
  }

  return (
    <div
      className="flex flex-wrap items-center gap-3 px-6 py-[10px] border-b border-border shrink-0"
      style={{ background: 'oklch(0.14 0.008 75)' }}
    >
      <span className="text-[10px] font-semibold tracking-[0.08em] uppercase" style={{ color: 'var(--dim)' }}>
        System:
      </span>
      <select
        style={selectStyle}
        value={localTargetOrg}
        onChange={e => setLocalTargetOrg(e.target.value)}
      >
        {TARGET_ORGS.map(o => <option key={o}>{o}</option>)}
      </select>

      <span className="text-[10px] font-semibold tracking-[0.08em] uppercase" style={{ color: 'var(--dim)' }}>
        Level:
      </span>
      <select
        style={selectStyle}
        value={localStatus}
        onChange={e => setLocalStatus(e.target.value)}
      >
        {LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
      </select>

      <div className="w-px h-[18px] shrink-0" style={{ background: 'var(--border)' }} />

      <button
        onClick={handleApply}
        style={{
          ...btnBase,
          background:  'var(--accent-dim)',
          color:       'var(--accent-text)',
          border:      '1px solid oklch(0.78 0.14 82 / 0.25)',
        }}
      >
        Execute
      </button>
      <button
        onClick={onReset}
        style={{
          ...btnBase,
          background: 'transparent',
          color:      'var(--muted)',
          border:     '1px solid var(--border)',
        }}
      >
        Reset
      </button>
    </div>
  )
}
