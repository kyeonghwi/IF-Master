'use client'

import { useRequireAuth } from '@/hooks/useAuth'
import { Sidebar } from '@/components/Sidebar'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  useRequireAuth()

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg)' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        {children}
      </div>
    </div>
  )
}
