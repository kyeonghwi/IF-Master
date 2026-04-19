'use client'

import { useState, useEffect } from 'react'
import type { InterfaceConfig, InterfaceConfigCreate } from '@/lib/types'

interface Props {
  open: boolean
  initial?: InterfaceConfig | null
  onSave: (data: InterfaceConfigCreate) => Promise<void>
  onClose: () => void
}

const PROTOCOLS = ['REST', 'SOAP', 'MQ', 'BATCH', 'SFTP'] as const

const EMPTY: InterfaceConfigCreate = {
  name: '',
  protocol: 'REST',
  target_org: '',
  endpoint_url: '',
  timeout_ms: 5000,
  max_retry: 3,
  enabled: true,
  schedule_cron: null,
  description: null,
}

function validate(f: InterfaceConfigCreate): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!f.name.trim()) errors.name = '이름을 입력하세요'
  else if (f.name.length > 100) errors.name = '최대 100자'
  if (!f.target_org.trim()) errors.target_org = '대상기관을 입력하세요'
  if (!f.endpoint_url.trim()) errors.endpoint_url = 'URL/경로를 입력하세요'
  if (f.timeout_ms < 100 || f.timeout_ms > 300000) errors.timeout_ms = '100~300000 ms'
  if (f.max_retry < 0 || f.max_retry > 10) errors.max_retry = '0~10'
  return errors
}

export function InterfaceFormModal({ open, initial, onSave, onClose }: Props) {
  const [form, setForm] = useState<InterfaceConfigCreate>(EMPTY)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(initial
        ? {
            name: initial.name,
            protocol: initial.protocol,
            target_org: initial.target_org,
            endpoint_url: initial.endpoint_url,
            timeout_ms: initial.timeout_ms,
            max_retry: initial.max_retry,
            enabled: initial.enabled,
            schedule_cron: initial.schedule_cron,
            description: initial.description,
          }
        : EMPTY
      )
      setErrors({})
    }
  }, [open, initial])

  if (!open) return null

  function set(field: keyof InterfaceConfigCreate, value: unknown) {
    setForm(prev => ({ ...prev, [field]: value }))
    setErrors(prev => ({ ...prev, [field]: '' }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSaving(true)
    try {
      await onSave(form)
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div
        className="relative z-10 rounded-md border border-border w-[520px] max-h-[90vh] overflow-y-auto"
        style={{ background: 'oklch(0.16 0.008 75)' }}
      >
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-[14px] font-semibold text-text">
            {initial ? '인터페이스 수정' : '인터페이스 등록'}
          </h3>
          <button onClick={onClose} className="text-muted hover:text-text text-[18px] leading-none">×</button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <Field label="이름 *" error={errors.name}>
            <input
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="금감원 보험계약 조회"
              className={inputCls(errors.name)}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="프로토콜 *">
              <select value={form.protocol} onChange={e => set('protocol', e.target.value)} className={inputCls()}>
                {PROTOCOLS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="대상기관 *" error={errors.target_org}>
              <input
                value={form.target_org}
                onChange={e => set('target_org', e.target.value)}
                placeholder="금감원"
                className={inputCls(errors.target_org)}
              />
            </Field>
          </div>

          <Field label="엔드포인트 URL / 경로 *" error={errors.endpoint_url}>
            <input
              value={form.endpoint_url}
              onChange={e => set('endpoint_url', e.target.value)}
              placeholder="https://api.example.com/v1/... 또는 /batch/jobs/..."
              className={inputCls(errors.endpoint_url)}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="타임아웃 (ms) *" error={errors.timeout_ms}>
              <input
                type="number"
                value={form.timeout_ms}
                onChange={e => set('timeout_ms', Number(e.target.value))}
                className={inputCls(errors.timeout_ms)}
              />
            </Field>
            <Field label="최대 재시도 *" error={errors.max_retry}>
              <input
                type="number"
                value={form.max_retry}
                onChange={e => set('max_retry', Number(e.target.value))}
                className={inputCls(errors.max_retry)}
              />
            </Field>
          </div>

          <Field label="스케줄 (cron, 선택)">
            <input
              value={form.schedule_cron ?? ''}
              onChange={e => set('schedule_cron', e.target.value || null)}
              placeholder="0 2 * * * (매일 02:00)"
              className={inputCls()}
            />
          </Field>

          <Field label="설명 (선택)">
            <input
              value={form.description ?? ''}
              onChange={e => set('description', e.target.value || null)}
              placeholder="인터페이스 용도 설명"
              className={inputCls()}
            />
          </Field>

          <div className="flex items-center gap-2">
            <input
              id="enabled"
              type="checkbox"
              checked={form.enabled}
              onChange={e => set('enabled', e.target.checked)}
              className="accent-accent"
            />
            <label htmlFor="enabled" className="text-[13px] text-muted cursor-pointer">활성화</label>
          </div>

          <div className="flex gap-2 justify-end pt-2 border-t border-border">
            <button type="button" onClick={onClose} className="px-4 py-[7px] text-[12px] rounded border border-border text-muted hover:text-text transition-colors">
              취소
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-[7px] text-[12px] rounded font-medium bg-accent/20 text-accent hover:bg-accent/30 border border-accent/40 disabled:opacity-50 transition-colors"
            >
              {saving ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] text-muted mb-1">{label}</label>
      {children}
      {error && <p className="text-[11px] text-danger mt-1">{error}</p>}
    </div>
  )
}

function inputCls(error?: string) {
  return `w-full px-3 py-[7px] text-[13px] rounded border ${error ? 'border-danger/60' : 'border-border'} bg-transparent text-text placeholder:text-dim focus:outline-none focus:border-accent/60 transition-colors`
}
