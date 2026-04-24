'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { InterfaceConfig, InterfaceConfigCreate, InterfaceConfigListResponse, ExecuteResult } from '@/lib/types'
import { authFetch, ApiError } from '@/lib/api'
import { Topbar } from '@/components/Topbar'
import { ProtocolBadge } from '@/components/ProtocolBadge'
import { InterfaceFormModal } from '@/components/InterfaceFormModal'
import { ConfirmDialog } from '@/components/ConfirmDialog'

type Toast = { msg: string; type: 'success' | 'danger' | 'warning' }

function useToast() {
  const [toast, setToast] = useState<Toast | null>(null)
  function show(msg: string, type: Toast['type'] = 'success') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }
  return { toast, show }
}

export default function InterfacesPage() {
  const qc = useQueryClient()
  const { toast, show } = useToast()

  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<InterfaceConfig | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<InterfaceConfig | null>(null)
  const [toggleTarget, setToggleTarget] = useState<InterfaceConfig | null>(null)
  const [executingIds, setExecutingIds] = useState<Set<string>>(new Set())

  const { data, isLoading } = useQuery<InterfaceConfigListResponse>({
    queryKey: ['interfaces'],
    queryFn: () => authFetch<InterfaceConfigListResponse>('/api/interfaces?size=100'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => authFetch(`/api/interfaces/${id}`, { method: 'DELETE' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['interfaces'] }); show('삭제되었습니다') },
    onError: (e: ApiError) => show(e.message, 'danger'),
  })

  const toggleMutation = useMutation({
    mutationFn: (id: string) => authFetch<InterfaceConfig>(`/api/interfaces/${id}/toggle`, { method: 'PATCH' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['interfaces'] }),
    onError: (e: ApiError) => show(e.message, 'danger'),
  })

  async function handleSave(formData: InterfaceConfigCreate) {
    if (editTarget) {
      await authFetch<InterfaceConfig>(`/api/interfaces/${editTarget.id}`, {
        method: 'PUT',
        body: JSON.stringify(formData),
      })
      show('수정되었습니다')
    } else {
      await authFetch<InterfaceConfig>('/api/interfaces', {
        method: 'POST',
        body: JSON.stringify(formData),
      })
      show('등록되었습니다')
    }
    qc.invalidateQueries({ queryKey: ['interfaces'] })
  }

  async function handleExecute(cfg: InterfaceConfig) {
    setExecutingIds(s => new Set(s).add(cfg.id))
    try {
      const result = await authFetch<ExecuteResult>(`/api/interfaces/${cfg.id}/execute`, { method: 'POST' })
      show(
        `${cfg.name}: ${result.message}${result.response_ms ? ` (${result.response_ms}ms)` : ''}`,
        result.status === 'SUCCESS' ? 'success' : 'danger',
      )
      qc.invalidateQueries({ queryKey: ['interfaces'] })
    } catch (e) {
      show(e instanceof ApiError ? e.message : '실행 실패', 'danger')
    } finally {
      setExecutingIds(s => { const n = new Set(s); n.delete(cfg.id); return n })
    }
  }

  const items = data?.items ?? []

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="인터페이스 관리" subtitle="IF Registry" />

      <div className="flex-1 px-6 py-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-[18px] font-semibold text-text">인터페이스 관리</h1>
            <p className="text-[12px] text-muted mt-[3px]">
              외부 기관 연계 인터페이스를 등록하고 온디맨드 테스트 실행을 수행합니다
            </p>
          </div>
          <button
            onClick={() => { setEditTarget(null); setModalOpen(true) }}
            className="px-4 py-[7px] text-[12px] font-medium rounded border border-accent/40 bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
          >
            + 신규 등록
          </button>
        </div>

        {/* Table */}
        <div className="rounded-md border border-border overflow-hidden">
          {isLoading ? (
            <TableSkeleton />
          ) : items.length === 0 ? (
            <EmptyState onAdd={() => { setEditTarget(null); setModalOpen(true) }} />
          ) : (
            <table className="w-full text-[13px]">
              <thead>
                <tr style={{ background: 'oklch(0.16 0.008 75)' }} className="border-b border-border">
                  <Th>이름</Th>
                  <Th>상태</Th>
                  <Th>프로토콜</Th>
                  <Th>대상기관</Th>
                  <Th>엔드포인트</Th>
                  <Th>타임아웃</Th>
                  <Th>스케줄</Th>
                  <Th align="right">액션</Th>
                </tr>
              </thead>
              <tbody>
                {items.map(cfg => (
                  <tr
                    key={cfg.id}
                    className="border-b border-border last:border-0 hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-text">{cfg.name}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => cfg.enabled ? setToggleTarget(cfg) : toggleMutation.mutate(cfg.id)}
                        title={cfg.enabled ? '클릭하여 비활성화' : '클릭하여 활성화'}
                        className={`inline-flex items-center px-[7px] py-[2px] rounded-[2px] text-[10px] font-bold tracking-[0.05em] uppercase cursor-pointer transition-opacity hover:opacity-70 ${
                          cfg.enabled ? 'bg-success-dim text-success' : 'bg-zinc-800 text-zinc-400'
                        }`}
                      >
                        {cfg.enabled ? 'ON' : 'OFF'}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <ProtocolBadge protocol={cfg.protocol} />
                    </td>
                    <td className="px-4 py-3 text-muted">{cfg.target_org}</td>
                    <td className="px-4 py-3 text-muted max-w-[200px] truncate" title={cfg.endpoint_url}>
                      {cfg.endpoint_url}
                    </td>
                    <td className="px-4 py-3 text-muted">{cfg.timeout_ms.toLocaleString()}ms</td>
                    <td className="px-4 py-3 text-muted text-[11px]">
                      {cfg.schedule_cron ? (
                        <code
                          className="inline-block font-mono text-[11px] rounded-[2px] border border-border"
                          style={{
                            padding: '2px 6px',
                            background: 'rgba(255,255,255,0.05)',
                            color: 'var(--muted)',
                          }}
                        >
                          {cfg.schedule_cron}
                        </code>
                      ) : (
                        <span style={{ color: 'var(--dim)' }}>—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 justify-end">
                        <ActionBtn
                          onClick={() => handleExecute(cfg)}
                          disabled={executingIds.has(cfg.id) || !cfg.enabled}
                          loading={executingIds.has(cfg.id)}
                          color="accent"
                          title={cfg.enabled ? '테스트 실행' : '비활성화 상태'}
                        >
                          {executingIds.has(cfg.id) ? '실행 중' : '실행'}
                        </ActionBtn>
                        <ActionBtn onClick={() => { setEditTarget(cfg); setModalOpen(true) }} color="muted">수정</ActionBtn>
                        <ActionBtn onClick={() => setDeleteTarget(cfg)} color="danger">삭제</ActionBtn>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <p className="text-[11px] text-dim mt-3">총 {data?.total ?? 0}개</p>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 px-4 py-3 rounded-md text-[13px] font-medium shadow-lg z-50 ${
            toast.type === 'success' ? 'bg-success-dim text-success border border-success/30' :
            toast.type === 'danger'  ? 'bg-danger-dim text-danger border border-danger/30' :
                                       'bg-warning-dim text-warning border border-warning/30'
          }`}
        >
          {toast.msg}
        </div>
      )}

      <InterfaceFormModal
        open={modalOpen}
        initial={editTarget}
        onSave={handleSave}
        onClose={() => setModalOpen(false)}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="인터페이스 삭제"
        message={`"${deleteTarget?.name}"을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`}
        confirmLabel="삭제"
        danger
        onConfirm={() => { deleteMutation.mutate(deleteTarget!.id); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />

      <ConfirmDialog
        open={!!toggleTarget}
        title="인터페이스 비활성화"
        message={`"${toggleTarget?.name}"을(를) 비활성화하면 진행 중인 호출이 중단될 수 있습니다. 계속하시겠습니까?`}
        confirmLabel="비활성화"
        danger
        onConfirm={() => { toggleMutation.mutate(toggleTarget!.id); setToggleTarget(null) }}
        onCancel={() => setToggleTarget(null)}
      />
    </div>
  )
}

function Th({ children, align }: { children: React.ReactNode; align?: 'right' }) {
  return (
    <th className={`px-4 py-3 text-[11px] font-medium text-muted uppercase tracking-[0.05em] ${align === 'right' ? 'text-right' : 'text-left'}`}>
      {children}
    </th>
  )
}

function ActionBtn({
  children, onClick, disabled, loading, color, title,
}: {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  color: 'accent' | 'muted' | 'danger'
  title?: string
}) {
  const colorCls = {
    accent: 'text-accent border-accent/30 hover:bg-accent/10',
    muted:  'text-muted border-border hover:bg-white/5',
    danger: 'text-danger border-danger/30 hover:bg-danger/10',
  }[color]

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
      className={`px-2 py-[4px] text-[11px] rounded border transition-colors disabled:opacity-40 ${colorCls}`}
    >
      {loading ? <span className="opacity-60">{children}</span> : children}
    </button>
  )
}

function TableSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-10 rounded bg-white/5 animate-pulse" />
      ))}
    </div>
  )
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-[14px] text-muted mb-1">등록된 인터페이스가 없습니다</p>
      <p className="text-[12px] text-dim mb-4">외부 기관 연계 인터페이스를 등록하면 온디맨드 테스트 실행이 가능합니다</p>
      <button
        onClick={onAdd}
        className="px-4 py-[7px] text-[12px] font-medium rounded border border-accent/40 bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
      >
        + 첫 인터페이스 등록
      </button>
    </div>
  )
}
