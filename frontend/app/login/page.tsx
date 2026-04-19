'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { login, ApiError } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  async function handleSubmit(u = username, p = password) {
    if (!u || !p) { setError('아이디와 비밀번호를 입력해주세요'); return }
    setLoading(true)
    setError('')
    try {
      await login(u, p)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  function handleDemoClick() {
    handleSubmit('test_admin', 'demo1234')
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center relative"
      style={{ background: 'var(--bg)' }}
    >
      {/* Subtle grid texture */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(oklch(0.22 0.006 75 / 0.18) 1px, transparent 1px), linear-gradient(90deg, oklch(0.22 0.006 75 / 0.18) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative z-10 w-full max-w-[380px] px-6">

        {/* Brand */}
        <div className="mb-9">
          <div className="flex items-center gap-[10px] mb-2">
            <div
              className="flex items-center justify-center shrink-0"
              style={{ width: 28, height: 28, border: '1.5px solid var(--accent)' }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="1" y="1" width="5" height="5" stroke="var(--accent)" strokeWidth="1.2"/>
                <rect x="8" y="1" width="5" height="5" stroke="var(--accent)" strokeWidth="1.2" fill="oklch(0.78 0.14 82 / 0.2)"/>
                <rect x="1" y="8" width="5" height="5" stroke="var(--accent)" strokeWidth="1.2" fill="oklch(0.78 0.14 82 / 0.2)"/>
                <rect x="8" y="8" width="5" height="5" stroke="var(--accent)" strokeWidth="1.2"/>
              </svg>
            </div>
            <span
              className="font-display font-bold text-[16px] tracking-[0.16em] uppercase"
              style={{ color: 'var(--accent)' }}
            >
              IF-Master
            </span>
          </div>
          <div
            className="text-[11px] tracking-[0.06em] uppercase pl-[38px]"
            style={{ color: 'var(--dim)' }}
          >
            Interface Control &amp; Retry Platform
          </div>
        </div>

        {/* Card */}
        <div
          className="border border-border"
          style={{ background: 'var(--surface)' }}
        >
          {/* Card header */}
          <div className="px-5 py-4 border-b border-border">
            <div
              className="font-display font-semibold text-[13px] tracking-[0.10em] uppercase"
              style={{ color: 'var(--muted)' }}
            >
              Operator Authentication
            </div>
          </div>

          {/* Card body */}
          <div className="p-5 flex flex-col gap-[14px]">

            {/* Username */}
            <div className="flex flex-col gap-[5px]">
              <label className="text-[10px] font-semibold tracking-[0.08em] uppercase" style={{ color: 'var(--dim)' }}>
                Username
              </label>
              <input
                type="text"
                autoComplete="username"
                spellCheck={false}
                value={username}
                onChange={e => setUsername(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                className="bg-bg border border-border text-text text-[13px] px-3 py-2 outline-none transition-colors"
                style={{ borderRadius: 2, fontFamily: 'var(--font-sans)' }}
                onFocus={e => (e.target.style.borderColor = 'oklch(0.78 0.14 82 / 0.5)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
              />
            </div>

            {/* Password */}
            <div className="flex flex-col gap-[5px]">
              <label className="text-[10px] font-semibold tracking-[0.08em] uppercase" style={{ color: 'var(--dim)' }}>
                Password
              </label>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                className="bg-bg border border-border text-text text-[13px] px-3 py-2 outline-none transition-colors"
                style={{ borderRadius: 2, fontFamily: 'var(--font-mono)' }}
                onFocus={e => (e.target.style.borderColor = 'oklch(0.78 0.14 82 / 0.5)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
              />
              {error && (
                <div className="text-[11px] min-h-4" style={{ color: 'var(--danger)' }} role="alert">
                  {error}
                </div>
              )}
            </div>

            {/* Sign In */}
            <button
              onClick={() => handleSubmit()}
              disabled={loading}
              className="w-full py-[10px] text-[12px] font-semibold tracking-[0.06em] uppercase cursor-pointer transition-opacity disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-85"
              style={{
                background: 'var(--accent)',
                color: 'oklch(0.12 0.008 75)',
                borderRadius: 2,
                border: 'none',
                fontFamily: 'var(--font-sans)',
              }}
            >
              {loading ? 'Authenticating\u2026' : 'Sign In'}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-border" />
              <span className="text-[10px] tracking-[0.06em] uppercase" style={{ color: 'var(--dim)' }}>or</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            {/* Demo button */}
            <button
              onClick={handleDemoClick}
              disabled={loading}
              className="w-full py-[10px] text-[12px] font-semibold tracking-[0.06em] uppercase cursor-pointer transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: 'transparent',
                color: 'var(--muted)',
                borderRadius: 2,
                border: '1px solid var(--border)',
                fontFamily: 'var(--font-sans)',
              }}
              onMouseEnter={e => {
                const t = e.currentTarget
                t.style.borderColor = 'var(--accent)'
                t.style.color = 'var(--accent-text)'
              }}
              onMouseLeave={e => {
                const t = e.currentTarget
                t.style.borderColor = 'var(--border)'
                t.style.color = 'var(--muted)'
              }}
            >
              One-click Demo Access
            </button>

            {/* Demo note */}
            <p
              className="text-center text-[10px] leading-relaxed"
              style={{ color: 'var(--dim)', fontFamily: 'var(--font-mono)' }}
            >
              <span style={{ color: 'var(--muted)' }}>test_admin</span>
              {' / '}
              <span style={{ color: 'var(--muted)' }}>demo1234</span>
              {' \u2014 읽기 전용 데모 환경'}
            </p>

          </div>
        </div>

      </div>
    </div>
  )
}
