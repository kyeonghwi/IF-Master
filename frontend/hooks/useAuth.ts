'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authFetch, ApiError } from '@/lib/api'

export function useRequireAuth() {
  const router = useRouter()
  useEffect(() => {
    authFetch('/api/stats').catch((err) => {
      if (err instanceof ApiError && err.status === 401) {
        router.replace('/login')
      }
    })
  }, [router])
}
