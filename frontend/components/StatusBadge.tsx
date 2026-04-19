import clsx from 'clsx'
import type { Status } from '@/lib/types'

interface Props {
  status: Status
  className?: string
}

const VARIANT: Record<Status, string> = {
  SUCCESS: 'bg-success-dim text-success',
  FAILED:  'bg-danger-dim text-danger',
  PENDING: 'bg-warning-dim text-warning',
}

const LABEL: Record<Status, string> = {
  SUCCESS: 'SUCCESS',
  FAILED:  'FAILED',
  PENDING: 'PENDING',
}

export function StatusBadge({ status, className }: Props) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-[7px] py-[2px] rounded-[2px]',
        'text-[10px] font-bold tracking-[0.05em] uppercase',
        VARIANT[status],
        className,
      )}
    >
      {LABEL[status]}
    </span>
  )
}
