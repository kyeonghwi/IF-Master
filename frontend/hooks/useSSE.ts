'use client'

import { useEffect, useRef } from 'react'
import type { SSETransaction, SSERetryResult } from '@/lib/types'
import { SSE_URL } from '@/lib/api'

interface SSEHandlers {
  onTransaction?: (data: SSETransaction) => void
  onRetryResult?: (data: SSERetryResult) => void
  onConnected?: () => void
  onDisconnected?: () => void
}

export function useSSE(handlers: SSEHandlers) {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    let es: EventSource | null = null
    let backoff = 1500
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      if (stopped) return
      es = new EventSource(SSE_URL)

      es.onopen = () => {
        backoff = 1500
        handlersRef.current.onConnected?.()
      }

      es.addEventListener('transaction', (e: MessageEvent) => {
        try {
          handlersRef.current.onTransaction?.(JSON.parse(e.data))
        } catch {}
      })

      es.addEventListener('retry_result', (e: MessageEvent) => {
        try {
          handlersRef.current.onRetryResult?.(JSON.parse(e.data))
        } catch {}
      })

      es.onerror = () => {
        es?.close()
        handlersRef.current.onDisconnected?.()
        if (!stopped) {
          timer = setTimeout(() => connect(), Math.min(backoff, 30_000))
          backoff = Math.min(backoff * 2, 30_000)
        }
      }
    }

    connect()

    return () => {
      stopped = true
      if (timer) clearTimeout(timer)
      es?.close()
    }
  }, [])
}
