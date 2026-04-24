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

export interface BulkRetryItem {
  log_id: string
  result: 'SUCCESS' | 'FAILED' | 'ALREADY_PROCESSED'
  message: string
}

export interface BulkRetryResponse {
  results: BulkRetryItem[]
}

// Interface Config
export type Protocol = 'REST' | 'SOAP' | 'MQ' | 'BATCH' | 'SFTP'

export interface InterfaceConfig {
  id: string
  name: string
  protocol: Protocol
  target_org: string
  endpoint_url: string
  timeout_ms: number
  max_retry: number
  enabled: boolean
  schedule_cron: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface InterfaceConfigListResponse {
  items: InterfaceConfig[]
  total: number
}

export interface InterfaceConfigCreate {
  name: string
  protocol: string
  target_org: string
  endpoint_url: string
  timeout_ms: number
  max_retry: number
  enabled: boolean
  schedule_cron: string | null
  description: string | null
}

export interface ExecuteResult {
  log_id: string
  status: string
  response_ms: number | null
  message: string
}

// Performance
export interface InterfacePerf {
  service_name: string
  protocol: string
  target_org: string
  call_count: number
  avg_ms: number
  p95_ms: number
  p99_ms: number
  sla_rate: number
}

export interface SlaSummary {
  total_calls: number
  within_sla: number
  sla_rate: number
}

export interface SlowAlert {
  service_name: string
  protocol: string
  p95_ms: number
  call_count: number
}

export interface PerformanceResponse {
  by_interface: InterfacePerf[]
  sla_summary: SlaSummary
  slow_alerts: SlowAlert[]
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
