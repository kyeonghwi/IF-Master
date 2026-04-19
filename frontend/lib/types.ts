export type Status = 'SUCCESS' | 'FAILED' | 'PENDING'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface SeriesPoint {
  timestamp: string  // ISO datetime
  success: number
  failed: number
  pending: number
}

export interface StatsResponse {
  total: number
  success: number
  failed: number
  pending: number
  series: SeriesPoint[]
}

export interface LogSummary {
  id: string
  idempotency_key: string
  target_org: string
  protocol: 'REST' | 'SOAP' | 'BATCH' | string
  service_name: string
  status: Status
  called_at: string
  responded_at: string | null
  retry_count: number
  error_message: string | null
}

export interface AuditLogEntry {
  id: string
  interface_log_id: string
  action: string
  operator: string
  executed_at: string
  result: string
  result_payload: string | null
}

export interface LogDetail extends LogSummary {
  request_payload: string | null
  response_payload: string | null
  stack_trace: string | null
  audit_logs: AuditLogEntry[]
}

export interface LogsResponse {
  items: LogSummary[]
  total: number
  page: number
  size: number
}

export interface RetryResult {
  result: 'SUCCESS' | 'FAILED' | 'ALREADY_PROCESSED'
  message: string
}

// SSE event payloads
export interface SSETransaction {
  id: string
  status: Status
  target_org: string
  called_at: string
}

export interface SSERetryResult {
  id: string
  result: string
  message: string
}
