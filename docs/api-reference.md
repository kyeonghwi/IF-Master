# API Reference — IF-Master

> Base URL (프로덕션): `https://if-master-api.onrender.com`  
> Base URL (로컬): `http://localhost:8000`  
> 인증: httpOnly Cookie (`access_token`) — 로그인 후 자동 세팅  
> 자동 생성 Swagger UI: `{Base URL}/docs`

---

## 인증

### POST /auth/login

데모 계정으로 로그인. JWT를 httpOnly Cookie로 발급.

**Request**
```json
{ "username": "test_admin", "password": "demo1234" }
```

**Response 200**
```json
{ "message": "로그인 성공", "username": "test_admin", "role": "ADMIN" }
```

Set-Cookie: `access_token=<JWT>; HttpOnly; Secure; SameSite=None`

---

### POST /auth/logout

Cookie 삭제.

**Response 200**
```json
{ "message": "로그아웃 성공" }
```

---

## 통계

### GET /api/stats

대시보드 상단 요약 지표 및 시계열 데이터.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| from_dt | datetime | 24시간 전 | 조회 시작 |
| to_dt | datetime | 현재 | 조회 종료 |

**Response 200**
```json
{
  "total": 1240,
  "success": 1185,
  "failed": 42,
  "pending": 13,
  "success_rate": 95.6,
  "timeseries": [
    { "hour": "2026-04-20T09:00:00", "success": 120, "failed": 5, "pending": 2 }
  ]
}
```

---

## 로그

### GET /api/logs

인터페이스 호출 로그 페이지네이션 조회.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| page | int | 1 | 페이지 번호 |
| size | int | 20 | 페이지 크기 |
| target_org | string | - | 대상 기관 필터 |
| protocol | string | - | 프로토콜 필터 |
| status | string | - | SUCCESS\|FAILED\|PENDING |
| from_dt | datetime | - | 조회 시작 |
| to_dt | datetime | - | 조회 종료 |

**Response 200**
```json
{
  "total": 42,
  "page": 1,
  "items": [
    {
      "id": "uuid",
      "idempotency_key": "금감원-20260420-a3f7c291",
      "target_org": "금감원",
      "protocol": "REST",
      "service_name": "보험료납입통보",
      "status": "FAILED",
      "error_message": "Connection timeout",
      "called_at": "2026-04-20T09:12:34",
      "response_ms": 5032,
      "retry_count": 0
    }
  ]
}
```

---

### GET /api/logs/{id}

특정 트랜잭션 상세 — Payload 전문 및 Audit Log 포함.

**Response 200**
```json
{
  "id": "uuid",
  "idempotency_key": "금감원-20260420-a3f7c291",
  "request_payload": "{\"source\": \"scheduler\"}",
  "response_payload": null,
  "error_message": "Connection timeout",
  "stack_trace": "...",
  "audit_logs": [
    {
      "action": "RETRY_REQUEST",
      "operator": "test_admin",
      "executed_at": "2026-04-20T09:15:00",
      "result": "SUCCESS"
    }
  ]
}
```

---

## 재처리

### POST /api/retry/{id}

실패 트랜잭션 재처리. 멱등성 보장 (외부 기관 상태 선조회).

**권한:** ADMIN, OPERATOR만 허용

**Response 200 — 정상 처리**
```json
{ "result": "SUCCESS", "message": "재처리 성공" }
```

**Response 200 — 이미 처리됨**
```json
{ "result": "ALREADY_PROCESSED", "message": "이미 처리됨 (멱등성 보장)" }
```

**Error Responses**

| 코드 | HTTP | 설명 |
|------|------|------|
| `FORBIDDEN` | 403 | 권한 없음 |
| `LOG_NOT_FOUND` | 404 | 트랜잭션 없음 |
| `NOT_RETRYABLE` | 400 | SUCCESS 상태 재처리 불가 |
| `RETRY_LIMIT_EXCEEDED` | 400 | 최대 3회 초과 |

---

## Interface Registry

### GET /api/interfaces

등록된 인터페이스 목록.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| page | int | 1 | 페이지 번호 |
| size | int | 20 | 페이지 크기 |
| enabled | bool | - | 활성 여부 필터 |

**Response 200**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "금감원 보험계약 조회",
      "protocol": "REST",
      "target_org": "금감원",
      "endpoint_url": "https://mock.example.com/fss/contracts",
      "timeout_ms": 5000,
      "max_retry": 3,
      "enabled": true,
      "schedule_cron": null,
      "description": "보험계약 정보 조회 API",
      "created_at": "2026-04-20T00:00:00",
      "updated_at": "2026-04-20T00:00:00"
    }
  ],
  "total": 10
}
```

---

### POST /api/interfaces

인터페이스 신규 등록.

**Request Body**
```json
{
  "name": "금감원 보험계약 조회",
  "protocol": "REST",
  "target_org": "금감원",
  "endpoint_url": "https://mock.example.com/fss/contracts",
  "timeout_ms": 5000,
  "max_retry": 3,
  "enabled": true,
  "schedule_cron": null,
  "description": "보험계약 정보 조회 API"
}
```

`protocol` 허용값: `REST` | `SOAP` | `MQ` | `BATCH` | `SFTP`

**Response 201** — 생성된 InterfaceConfig 반환

---

### PUT /api/interfaces/{id}

설정 수정. 변경할 필드만 전송 (partial update).

**Request Body** — 모든 필드 optional
```json
{
  "timeout_ms": 3000,
  "enabled": false
}
```

**Response 200** — 수정된 InterfaceConfig 반환

**Error:** `NOT_FOUND` 404

---

### PATCH /api/interfaces/{id}/toggle

`enabled` ON ↔ OFF 토글.

**Response 200** — 토글된 InterfaceConfig 반환

---

### DELETE /api/interfaces/{id}

인터페이스 삭제.

**Response 204 No Content**

---

### POST /api/interfaces/{id}/execute

온디맨드 즉시 실행. 결과를 `interface_log`에 기록하고 SSE broadcast.

**권한:** 로그인 필요

**Response 200**
```json
{
  "log_id": "uuid",
  "status": "SUCCESS",
  "response_ms": 342,
  "message": "실행 성공"
}
```

**Error Responses**

| 코드 | HTTP | 설명 |
|------|------|------|
| `NOT_FOUND` | 404 | 인터페이스 없음 |
| `INTERFACE_DISABLED` | 400 | 비활성 인터페이스 |

---

## 성능 관리

### GET /api/performance

인터페이스별 응답시간 P95/P99 및 SLA 준수율 집계.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| from_dt | datetime | 24시간 전 | 집계 시작 |
| to_dt | datetime | 현재 | 집계 종료 |
| protocol | string | - | 프로토콜 필터 |
| target_org | string | - | 기관 필터 |

**Response 200**
```json
{
  "by_interface": [
    {
      "service_name": "손해율 배치",
      "protocol": "BATCH",
      "target_org": "내부",
      "call_count": 52,
      "avg_ms": 15200.0,
      "p95_ms": 28432.0,
      "p99_ms": 29800.0,
      "sla_rate": 12.5
    }
  ],
  "sla_summary": {
    "total_calls": 1240,
    "within_sla": 1225,
    "sla_rate": 98.8
  },
  "slow_alerts": [
    {
      "service_name": "손해율 배치",
      "protocol": "BATCH",
      "p95_ms": 28432.0,
      "call_count": 52
    }
  ]
}
```

SLA 기준: `response_ms < 3000ms`  
`slow_alerts`: P95 > 3000ms인 인터페이스 목록

---

## 실시간 스트림

### GET /api/stream

SSE(Server-Sent Events) 엔드포인트. 로그인 후 연결 유지.

**이벤트 타입**

| 이벤트 | 발생 시점 | 데이터 |
|--------|---------|--------|
| `new_tx` | APScheduler 30초 자동 생성 | `{id, status, service_name, ...}` |
| `retry_result` | 재처리 완료 | `{id, result, message}` |
| `execution_result` | 온디맨드 실행 완료 | `{id, result, service_name, response_ms}` |
| `ping` | 30초마다 keepalive | `{}` |

**연결 예시 (JavaScript)**
```javascript
const es = new EventSource('/api/stream', { withCredentials: true });
es.addEventListener('retry_result', (e) => {
  const data = JSON.parse(e.data);
  showToast(data.message);
});
```

---

## Mock 서버

### GET /mock/status

idempotency_key로 처리 여부 조회.

**Query:** `key={idempotency_key}`

**Response**
```json
// 처리된 경우
{ "status": "SUCCESS", "response": { ... } }

// 미처리
{ "status": "not_found" }
```

---

### POST /mock/call

idempotency_key로 외부 기관 호출 시뮬레이션.

**Query:** `key={idempotency_key}`

프로토콜별 응답 특성은 `mock_service.dispatch()` 참조.
