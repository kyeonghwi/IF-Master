'use client'

import { useEffect, useState } from 'react'
import { getUsername } from '@/lib/api'

interface Props {
  title: string
  subtitle: string
  connected?: boolean
  children?: React.ReactNode
}

export function Topbar({ title, subtitle, connected = false, children }: Props) {
  const [clock, setClock] = useState('')
  const [user,  setUser]  = useState('')

  useEffect(() => {
    setUser(getUsername() ?? '—')
    function tick() {
      setClock(
        new Date().toLocaleString('ko-KR', {
          timeZone: 'Asia/Seoul',
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit',
          hour12: false,
        }).replace(/\. /g, '-').replace(/\.$/, '').replace(', ', ' ') + ' KST'
      )
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div
      className="flex items-center px-6 gap-3 shrink-0 border-b border-border"
      style={{ height: 50 }}
    >
      {/* Live dot */}
      <span
        className="w-[6px] h-[6px] rounded-full shrink-0 transition-colors duration-300"
        style={{
          background:  connected ? 'var(--success)' : 'oklch(0.65 0.18 28 / 0.6)',
          animation:   connected ? 'pulse 2s infinite' : 'none',
        }}
      />

      {/* Title */}
      <span
        className="font-display font-semibold text-[14px] tracking-[0.08em] uppercase"
        style={{ color: 'var(--text)' }}
      >
        {title}
      </span>

      {/* Sep */}
      <span className="w-px h-[14px] bg-border shrink-0" />

      {/* Subtitle */}
      <span className="text-[12px]" style={{ color: 'var(--dim)' }}>
        {subtitle}
      </span>

      {/* Right actions */}
      <div className="ml-auto flex items-center gap-2">
        <span
          className="font-mono text-[11px]"
          style={{ color: 'var(--dim)' }}
        >
          {clock}
        </span>
        {user && (
          <span
            className="text-[11px] px-2 py-[2px] rounded-[2px]"
            style={{ color: 'var(--muted)', background: 'var(--surface-2)' }}
          >
            {user}
          </span>
        )}
        {children}
      </div>
    </div>
  )
}
