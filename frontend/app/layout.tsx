import type { Metadata } from 'next'
import { Barlow_Condensed, Geist_Mono } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const barlowCondensed = Barlow_Condensed({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-display',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'IF-Master — Interface Control Tower',
  description: '보험사 금융 인터페이스 통합 관제 시스템',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css"
        />
        <style>{`
          :root {
            --font-sans: 'Pretendard Variable', Pretendard, -apple-system, sans-serif;
          }
          body { font-family: var(--font-sans); font-size: 14px; line-height: 1.55; }
        `}</style>
      </head>
      <body className={`${barlowCondensed.variable} ${geistMono.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
