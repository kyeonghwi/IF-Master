import type { Status } from './types'

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 23)
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return iso.slice(11, 23)
}

export function formatLatency(
  calledAt: string | null | undefined,
  respondedAt: string | null | undefined,
): { text: string; variant: 'normal' | 'warning' | 'danger' } {
  if (!respondedAt) return { text: 'timeout', variant: 'danger' }
  const ms = new Date(respondedAt).getTime() - new Date(calledAt!).getTime()
  if (ms > 2000) return { text: `${ms}ms`, variant: 'danger' }
  if (ms > 500)  return { text: `${ms}ms`, variant: 'warning' }
  return { text: `${ms}ms`, variant: 'normal' }
}

export function statusVariant(status: Status): 'success' | 'danger' | 'warning' {
  if (status === 'SUCCESS') return 'success'
  if (status === 'FAILED')  return 'danger'
  return 'warning'
}

export function rowBg(status: Status): string {
  if (status === 'FAILED')  return 'bg-danger-dim'
  if (status === 'PENDING') return 'bg-warning-dim'
  return ''
}

export function clampNumber(n: number): string {
  return n.toLocaleString('ko-KR')
}

export function successRate(success: number, total: number): string {
  if (!total) return '—'
  return ((success / total) * 100).toFixed(1) + '%'
}
