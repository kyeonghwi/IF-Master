import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{ts,tsx}',
  ],
  safelist: [
    'bg-danger-dim', 'bg-warning-dim', 'bg-success-dim',
    'text-danger',   'text-warning',   'text-success',
  ],
  theme: {
    extend: {
      colors: {
        bg:       'var(--bg)',
        surface:  'var(--surface)',
        surface2: 'var(--surface-2)',
        surface3: 'var(--surface-3)',
        accent:   'var(--accent)',
        'accent-dim':  'var(--accent-dim)',
        'accent-text': 'var(--accent-text)',
        success:  'var(--success)',
        'success-dim': 'var(--success-dim)',
        danger:   'var(--danger)',
        'danger-dim':  'var(--danger-dim)',
        warning:  'var(--warning)',
        'warning-dim': 'var(--warning-dim)',
        border:   'var(--border)',
        text:     'var(--text)',
        muted:    'var(--muted)',
        dim:      'var(--dim)',
      },
      fontFamily: {
        display: ['var(--font-display)', 'sans-serif'],
        sans:    ['var(--font-sans)', 'sans-serif'],
        mono:    ['var(--font-mono)', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
