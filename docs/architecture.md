# 아키텍처 문서 — IF-Master

---

## 1. 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 (운영 담당자)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────┐
│               Frontend (Next.js 15 / Vercel)                    │
│                                                                 │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐  │
│  │  Control    │ │  Interface   │ │  Interface │ │ Perf     │  │
│  │  Tower      │ │  Logs        │ │  Registry  │ │ Mgmt     │  │
│  │ (대시보드)  │ │ (로그 조회)  │ │ (등록·실행)│ │ (P95/SLA)│  │
│  └─────────────┘ └──────────────┘ └────────────┘ └──────────┘  │
│                                                                 │
│  SSE EventSource (자동 재연결)     TanStack Table + Recharts    │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST + SSE + httpOnly Cookie
┌────────────────────────────▼────────────────────────────────────┐
│               Backend (FastAPI / Render)                        │
│                                                                 │
│  GET  /api/stats           → 24h 집계 + 시계열                  │
│  GET  /api/logs            → 페이지네이션 + 필터링              │
│  GET  /api/logs/{id}       → 상세 + Payload + AuditLog          │
│  POST /api/retry/{id}      → 멱등성 재처리 (FOR UPDATE)         │
│  GET  /api/interfaces      → Registry 목록                      │
│  POST /api/interfaces      → 신규 등록                          │
│  PUT  /api/interfaces/{id} → 설정 수정                          │
│  PATCH /api/interfaces/{id}/toggle → enabled ON/OFF             │
│  DELETE /api/interfaces/{id}       → 삭제                       │
│  POST /api/interfaces/{id}/execute → 온디맨드 실행              │
│  GET  /api/performance     → P95/P99/SLA 집계                   │
│  GET  /api/stream          → SSE broadcast (재처리·실행 결과)   │
│  POST /auth/login          → JWT 발급 (httpOnly Cookie)         │
│                                                                 │
│  APScheduler: 30초마다 1~3건 트랜잭션 자동 생성                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ asyncpg (SQLAlchemy async)
┌────────────────────────────▼────────────────────────────────────┐
│               PostgreSQL (Render)                               │
│                                                                 │
│  interface_config  — 인터페이스 등록·설정                       │
│  interface_log     — 전체 호출 이력 + response_ms               │
│  audit_log         — 재처리·실행 감사 이력                      │
│  mock_responses    — Mock 결과 저장 (멱등성 확인용)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. ERD

```
┌──────────────────────────────────────────────────────────────────┐
│                       interface_config                           │
├──────────────────────────────────────────────────────────────────┤
│ id            UUID         PK                                    │
│ name          VARCHAR(100) UNIQUE NOT NULL                       │
│ protocol      VARCHAR(10)  NOT NULL  -- REST|SOAP|MQ|BATCH|SFTP  │
│ target_org    VARCHAR(50)  NOT NULL                              │
│ endpoint_url  VARCHAR(300) NOT NULL                              │
│ timeout_ms    INTEGER      DEFAULT 5000                          │
│ max_retry     INTEGER      DEFAULT 3                             │
│ enabled       BOOLEAN      DEFAULT TRUE                          │
│ schedule_cron VARCHAR(50)  NULL  -- NULL = 온디맨드 전용         │
│ description   TEXT                                               │
│ created_at    TIMESTAMP    DEFAULT NOW()                         │
│ updated_at    TIMESTAMP    DEFAULT NOW()                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        interface_log                             │
├──────────────────────────────────────────────────────────────────┤
│ id               UUID        PK                                  │
│ idempotency_key  VARCHAR(64) UNIQUE NOT NULL  ← 멱등성 핵심      │
│ target_org       VARCHAR(50) NOT NULL                            │
│ protocol         VARCHAR(10) NOT NULL                            │
│ service_name     VARCHAR(100) NOT NULL                           │
│ status           VARCHAR(10) NOT NULL  -- SUCCESS|FAILED|PENDING │
│ request_payload  TEXT                                            │
│ response_payload TEXT                                            │
│ error_message    TEXT                                            │
│ stack_trace      TEXT                                            │
│ called_at        TIMESTAMP   NOT NULL   INDEX                    │
│ responded_at     TIMESTAMP   NULL                                │
│ retry_count      INTEGER      DEFAULT 0                          │
│ response_ms      INTEGER      NULL  ← 성능 집계 핵심             │
│ created_at       TIMESTAMP    DEFAULT NOW()                      │
└──────────────────────────┬───────────────────────────────────────┘
                           │ 1:N
┌──────────────────────────▼───────────────────────────────────────┐
│                          audit_log                               │
├──────────────────────────────────────────────────────────────────┤
│ id               UUID        PK                                  │
│ interface_log_id UUID        FK → interface_log.id               │
│ action           VARCHAR(20) NOT NULL                            │
│   -- RETRY_REQUEST | RETRY_SUCCESS | RETRY_SKIP | RETRY_FAILED   │
│   -- MANUAL_EXECUTE                                              │
│ operator         VARCHAR(50) NOT NULL  -- JWT sub (사용자명)     │
│ executed_at      TIMESTAMP   NOT NULL                            │
│ result           VARCHAR(30) NOT NULL                            │
│ result_payload   TEXT                                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        mock_responses                            │
├──────────────────────────────────────────────────────────────────┤
│ id               UUID        PK                                  │
│ idempotency_key  VARCHAR(64) UNIQUE NOT NULL                     │
│ status           VARCHAR(10) NOT NULL  -- SUCCESS|FAILED         │
│ response_json    TEXT                                            │
│ created_at       TIMESTAMP   DEFAULT NOW()                       │
└──────────────────────────────────────────────────────────────────┘
```

인덱스:
- `ix_interface_log_status` — 상태별 필터링
- `ix_interface_log_called_at` — 시간 범위 조회
- `ix_interface_config_enabled` — enabled 필터링

---

## 3. 멱등성 재처리 시퀀스

```
담당자         Frontend         Backend              Mock 서버
  │               │                │                    │
  │ [재처리] 클릭 │                │                    │
  ├─────────────►│                │                    │
  │              │ POST /api/retry/{id}                │
  │              ├───────────────►│                    │
  │              │                │                    │
  │              │                │ ① 권한 확인 (ADMIN|OPERATOR)
  │              │                │                    │
  │              │                │ ② SELECT FOR UPDATE (비관적 잠금)
  │              │                │   → 동시 재처리 Race Condition 방지
  │              │                │                    │
  │              │                │ ③ 상태 확인 (FAILED|PENDING만 허용)
  │              │                │                    │
  │              │                │ ④ AuditLog INSERT (RETRY_REQUEST)
  │              │                │                    │
  │              │                │ GET /mock/status?key={idempotency_key}
  │              │                ├───────────────────►│
  │              │                │◄───────────────────┤
  │              │                │                    │
  │              │  ┌─────────────▼─────────────────┐  │
  │              │  │ Case A: 이미 처리됨            │  │
  │              │  │ → log.status = SUCCESS         │  │
  │              │  │ → AuditLog (RETRY_SKIP)        │  │
  │              │  │ → "이미 처리됨 (멱등성 보장)"  │  │
  │              │  └───────────────────────────────┘  │
  │              │                │                    │
  │              │  ┌─────────────▼─────────────────┐  │
  │              │  │ Case B: 미처리                 │  │
  │              │  │   POST /mock/call?key={key}    │  │
  │              │  ├───────────────────────────────►│  │
  │              │  │◄───────────────────────────────┤  │
  │              │  │ → log.status 업데이트          │  │
  │              │  │ → AuditLog (RETRY_SUCCESS/     │  │
  │              │  │            RETRY_FAILED)       │  │
  │              │  └───────────────────────────────┘  │
  │              │                │                    │
  │              │                │ ⑤ COMMIT           │
  │              │                │                    │
  │              │                │ ⑥ SSE broadcast → 연결된 모든 클라이언트
  │              │◄───────────────┤                    │
  │◄─────────────┤                │                    │
  │ Toast 알림   │                │                    │
```

---

## 4. 온디맨드 실행 시퀀스

```
담당자         Frontend         Backend          mock_service
  │               │                │                  │
  │ [실행] 클릭   │                │                  │
  ├─────────────►│                │                  │
  │              │ POST /api/interfaces/{id}/execute  │
  │              ├───────────────►│                  │
  │              │                │                  │
  │              │                │ ① interface_config 조회
  │              │                │   enabled 확인 (false → 400)
  │              │                │                  │
  │              │                │ ② idempotency_key 생성
  │              │                │   {target_org[:6]}-{yyyyMMdd}-{uuid8}
  │              │                │                  │
  │              │                │ ③ interface_log INSERT (PENDING)
  │              │                │                  │
  │              │                │ dispatch(protocol, timeout_ms)
  │              │                ├─────────────────►│
  │              │                │  프로토콜별 지연·성공률 시뮬레이션
  │              │                │◄─────────────────┤
  │              │                │                  │
  │              │                │ ④ interface_log 업데이트
  │              │                │   (status, response_ms, response_payload)
  │              │                │                  │
  │              │                │ ⑤ AuditLog INSERT (MANUAL_EXECUTE)
  │              │                │                  │
  │              │                │ ⑥ COMMIT
  │              │                │                  │
  │              │                │ ⑦ SSE broadcast (execution_result)
  │              │◄───────────────┤                  │
  │◄─────────────┤                │                  │
  │ 결과 Toast   │                │                  │
```

---

## 5. SSE 실시간 이벤트 흐름

```
Backend (APScheduler)          Backend (SSE)          Frontend
        │                           │                     │
        │ 30초마다 트랜잭션 생성     │                     │
        │                           │                     │
        │ broadcast("new_tx", data) │                     │
        ├──────────────────────────►│                     │
        │                           │ EventSource stream  │
        │                           ├────────────────────►│
        │                           │                     │ 테이블 자동 갱신
        │                           │                     │
재처리 완료                          │                     │
        │ broadcast("retry_result") │                     │
        ├──────────────────────────►│                     │
        │                           ├────────────────────►│
        │                           │                     │ Toast 알림
        │                           │                     │
실행 완료                            │                     │
        │ broadcast("execution_result")                   │
        ├──────────────────────────►│                     │
        │                           ├────────────────────►│
        │                           │                     │ Toast 알림
```

이벤트 타입:
- `new_tx` — APScheduler가 자동 생성한 트랜잭션
- `retry_result` — 재처리 완료 결과
- `execution_result` — 온디맨드 실행 완료 결과
- `ping` — 30초 keepalive (연결 유지)

---

## 6. 배포 구조

```
GitHub (master)
    │
    ├─ Vercel (자동 배포)
    │   └─ frontend/
    │      NEXT_PUBLIC_API_URL=https://if-master-api.onrender.com
    │
    └─ Render (자동 배포)
        └─ backend/
           DATABASE_URL=postgresql+asyncpg://...
           JWT_SECRET=...
           FRONTEND_URL=https://ifmaster.vercel.app

Render PostgreSQL
    └─ 백엔드와 동일 리전 (Oregon)
       Cold start 방지: GitHub Actions 5분 cron ping
```
