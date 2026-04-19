'use client'

interface Props {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '확인',
  danger = false,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div
        className="relative z-10 rounded-md border border-border p-6 w-[360px]"
        style={{ background: 'oklch(0.16 0.008 75)' }}
      >
        <h3 className="text-[14px] font-semibold text-text mb-2">{title}</h3>
        <p className="text-[13px] text-muted mb-6">{message}</p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-[7px] text-[12px] rounded border border-border text-muted hover:text-text transition-colors"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-[7px] text-[12px] rounded font-medium transition-colors ${
              danger
                ? 'bg-danger/20 text-danger hover:bg-danger/30 border border-danger/40'
                : 'bg-accent/20 text-accent hover:bg-accent/30 border border-accent/40'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
