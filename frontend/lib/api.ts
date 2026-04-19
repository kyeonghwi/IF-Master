const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message)
  }
}

function extractMessage(body: Record<string, unknown>): string {
  if (typeof body?.message === 'string') return body.message
  const detail = body?.detail
  if (typeof detail === 'object' && detail !== null && 'message' in detail) {
    return String((detail as Record<string, unknown>).message)
  }
  if (Array.isArray(detail)) return detail.map((e: unknown) => (e as Record<string, unknown>).msg).join(', ')
  if (typeof detail === 'string') return detail
  return '요청 처리 중 오류가 발생했습니다'
}

export async function authFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (res.status === 401) {
    if (typeof window !== 'undefined') window.location.href = '/login'
    throw new ApiError(401, '인증이 필요합니다')
  }

  if (!res.ok) {
    let body: Record<string, unknown> = {}
    try { body = await res.json() } catch {}
    const msg = extractMessage(body)
    const code = typeof (body?.detail as Record<string, unknown>)?.code === 'string'
      ? String((body.detail as Record<string, unknown>).code)
      : undefined
    throw new ApiError(res.status, msg, code)
  }

  return res.json() as Promise<T>
}

export async function login(username: string, password: string): Promise<void> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    let body: Record<string, unknown> = {}
    try { body = await res.json() } catch {}
    throw new ApiError(res.status, extractMessage(body))
  }
}

export async function logout(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, { method: 'POST', credentials: 'include' })
}

export const SSE_URL = `${API_URL}/api/stream`
