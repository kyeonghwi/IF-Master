import clsx from 'clsx'
import type { Protocol } from '@/lib/types'

interface Props {
  protocol: string
  className?: string
}

const VARIANT: Record<string, string> = {
  REST:  'bg-blue-900/40 text-blue-300',
  SOAP:  'bg-purple-900/40 text-purple-300',
  MQ:    'bg-yellow-900/40 text-yellow-300',
  BATCH: 'bg-zinc-800 text-zinc-300',
  SFTP:  'bg-emerald-900/40 text-emerald-300',
}

export function ProtocolBadge({ protocol, className }: Props) {
  const key = protocol.toUpperCase()
  return (
    <span
      className={clsx(
        'inline-flex items-center px-[7px] py-[2px] rounded-[2px]',
        'text-[10px] font-bold tracking-[0.05em] uppercase',
        VARIANT[key] ?? 'bg-zinc-800 text-zinc-300',
        className,
      )}
    >
      {protocol.toUpperCase()}
    </span>
  )
}
