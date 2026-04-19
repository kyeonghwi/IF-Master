'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import clsx from 'clsx'
import { logout } from '@/lib/api'

const NAV = [
  { href: '/dashboard',   label: 'Control Tower' },
  { href: '/logs',        label: 'Interface Logs' },
  { href: '/interfaces',  label: 'IF Registry' },
  { href: '/performance', label: 'Performance' },
]

export function Sidebar() {
  const pathname = usePathname()
  const router   = useRouter()

  async function handleLogout(e: React.MouseEvent) {
    e.preventDefault()
    await logout()
    router.push('/login')
  }

  return (
    <nav
      style={{ background: 'oklch(0.14 0.008 75)', width: 216, minWidth: 216 }}
      className="flex flex-col h-screen sticky top-0 border-r border-border"
    >
      {/* Brand */}
      <div className="px-5 pt-[22px] pb-4 border-b border-border">
        <div
          className="font-display font-bold text-[15px] tracking-[0.14em] uppercase"
          style={{ color: 'var(--accent)' }}
        >
          IF-Master
        </div>
        <div className="text-[10px] mt-[3px] tracking-[0.05em] uppercase" style={{ color: 'var(--dim)' }}>
          Interface Control Platform
        </div>
      </div>

      {/* Nav */}
      <ul className="flex-1 py-2 list-none m-0 p-0">
        {NAV.map(({ href, label }) => {
          const active = pathname.startsWith(href)
          return (
            <li key={href}>
              <Link
                href={href}
                className={clsx(
                  'flex items-center justify-between px-5 py-[9px] text-[13px] no-underline transition-colors duration-100',
                  active
                    ? 'font-medium'
                    : 'hover:text-text',
                )}
                style={{
                  color:      active ? 'var(--text)'  : 'var(--muted)',
                  background: active ? 'var(--accent-dim)' : 'transparent',
                }}
              >
                {label}
              </Link>
            </li>
          )
        })}
      </ul>

      {/* Footer */}
      <div className="border-t border-border py-2">
        <a
          href="#"
          className="block px-5 py-[7px] text-[12px] no-underline transition-colors"
          style={{ color: 'var(--dim)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--muted)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--dim)')}
        >
          Support
        </a>
        <a
          href="#"
          onClick={handleLogout}
          className="block px-5 py-[7px] text-[12px] no-underline transition-colors"
          style={{ color: 'var(--dim)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--muted)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--dim)')}
        >
          Log Out
        </a>
      </div>
    </nav>
  )
}
