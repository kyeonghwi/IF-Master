# IF-Master — Interface Control & Retry Platform

> 보험사 대내외 인터페이스 통합 관제 및 재처리 시스템 (채용 포트폴리오)

**라이브 데모**: [ifmaster.vercel.app](https://ifmaster.vercel.app) — `test_admin / demo1234` 또는 원클릭 데모 버튼

---

## 무엇을 만들었나

보험사는 금감원, 결제대행사 등 외부 기관과 REST, SOAP, MQ, BATCH, SFTP 등 이종 프로토콜로 연동된다. 장애 발생 시 각 시스템 로그를 개별 조회해야 해서 원인 파악이 늦다. 이 시스템은 두 가지 문제를 직접 해결한다.

1. **가시성** — 모든 인터페이스 상태를 단일 화면에서 실시간 모니터링
2. **안전한 재처리** — 타임아웃 실패 트랜잭션 재처리 시 외부 기관 중복 처리 방지 (멱등성 보장)

---

## 주요 기능

### 1. 통합 모니터링 대시보드

APScheduler가 30초마다 트랜잭션을 자동 생성하고, SSE로 모든 클라이언트에 즉시 push한다. 빈 화면 없음.

### 2. 원클릭 재처리 — 멱등성 보장 (핵심)

```
재처리 요청
    │
    ├─ SELECT ... FOR UPDATE  ← 동시 재처리 Race Condition 방지
    │
    ├─ GET /mock/status?key={idempotency_key}
    │   ├─ 이미 처리됨 → DB SUCCESS, "이미 처리됨" 반환
    │   └─ 미처리 → POST /mock/call → 재전송
    │
    └─ AuditLog 기록 (실행자·시각·결과 전수 보존)
```

타임아웃 실패 트랜잭션이 실제로는 처리됐다면, 재처리 시 이중 출금·이중 보고가 발생한다. 이를 `SELECT ... FOR UPDATE` + 외부 상태 선조회로 방지한다.

### 3. Interface Registry + 온디맨드 실행

인터페이스를 등록하고 설정(타임아웃, 재시도, 프로토콜)을 관리한다. 등록된 인터페이스를 버튼 하나로 즉시 실행해 결과를 확인할 수 있다.

### 4. 성능 관리 (P95 / SLA)

```sql
PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms)
```

PostgreSQL 집계 함수로 인터페이스별 P95/P99 응답시간과 SLA 준수율을 계산한다. 3초 초과 인터페이스는 알림으로 표시된다.

### 5. 통합 로그 조회

프로토콜·기관·상태·기간 필터로 전체 호출 이력을 단일 테이블에서 조회한다. 행 클릭 시 Request/Response Payload 전문과 Audit Log를 확인할 수 있다.

---

## 아키텍처

```
┌─────────────────────────────────────────┐
│  Frontend (Next.js 15 / Vercel)         │
│  Control Tower | Logs | Registry | Perf │
│  TanStack Table + Recharts + shadcn/ui  │
│  SSE EventSource (자동 재연결)           │
└──────────────────┬──────────────────────┘
                   │ REST + SSE + httpOnly Cookie
┌──────────────────▼──────────────────────┐
│  Backend (FastAPI / Render)             │
│                                         │
│  /api/stats          통계 집계          │
│  /api/logs           로그 조회          │
│  /api/retry/{id}     멱등성 재처리      │
│  /api/interfaces     Registry CRUD      │
│  /api/interfaces/{id}/execute  실행     │
│  /api/performance    P95/SLA 집계       │
│  /api/stream         SSE broadcast      │
│  APScheduler         30초 자동 생성     │
└──────────────────┬──────────────────────┘
                   │ asyncpg
┌──────────────────▼──────────────────────┐
│  PostgreSQL (Render)                    │
│  interface_config  등록·설정            │
│  interface_log     호출 이력 + 응답시간 │
│  audit_log         감사 이력            │
│  mock_responses    멱등성 확인용        │
└─────────────────────────────────────────┘
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | Next.js 15, TanStack Table, Recharts, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), APScheduler |
| Database | PostgreSQL (Render) |
| 인증 | JWT HS256, httpOnly Cookie (XSS 방어) |
| 실시간 | SSE (Server-Sent Events) |
| 배포 | Vercel (프론트) + Render (백엔드 + DB) |
| CI | GitHub Actions (5분 cron ping — Render 콜드 스타트 방지) |

---

## 로컬 실행

```bash
# 1. DB 실행
docker-compose up -d

# 2. 백엔드
cd backend
pip install -e ".[dev]"
python -m scripts.seed          # 500건 시드 데이터
uvicorn app.main:app --reload

# 3. 프론트엔드
cd frontend
npm install
npm run dev
```

`.env` (백엔드):
```
DATABASE_URL=postgresql+asyncpg://ifmaster:ifmaster@localhost:5432/ifmaster
JWT_SECRET=your-secret-here
DEMO_USERNAME=test_admin
DEMO_PASSWORD=demo1234
FRONTEND_URL=http://localhost:3000
```

---

## 테스트

```bash
cd backend
pytest -v
```

주요 테스트:
- `test_idempotency.py` — 동일 ID 재처리 시 ALREADY_PROCESSED 반환 검증
- `test_interfaces.py` — Registry CRUD + 비활성 인터페이스 실행 거부 검증
- `test_performance.py` — P95 집계 및 SLA 수치 검증
- `test_mock_distribution.py` — `/mock/call` 성공률 분포 검증
- `test_sse_ping.py` — SSE 35초 내 ping 수신 검증

---

## 환경변수 (Render 배포 시)

| 변수 | 설명 |
|------|------|
| `DATABASE_URL` | Render PostgreSQL connection string |
| `JWT_SECRET` | 32자 이상 랜덤 문자열 |
| `DEMO_USERNAME` | 데모 계정 아이디 |
| `DEMO_PASSWORD` | 데모 계정 비밀번호 |
| `FRONTEND_URL` | Vercel 배포 URL |
| `COOKIE_SECURE` | `true` (Render HTTPS 환경) |

---

## 문서

| 문서 | 내용 |
|------|------|
| [기획서](docs/기획서.md) | 추진 배경 · 기능 정의 · AI 활용 계획 · 기대 효과 |
| [개발문서](docs/개발문서.md) | 시스템 아키텍처 · ERD · 멱등성 설계 · API 명세 · 데모 가이드 |
| [PRD](docs/prd.md) | 설계 의도 및 기술 결정 근거 (상세) |
| [Architecture](docs/architecture.md) | ERD + 시퀀스 다이어그램 (상세) |
| [API Reference](docs/api-reference.md) | 전체 엔드포인트 명세 |
| [Demo Guide](docs/demo-guide.md) | 심사자용 3분 데모 시나리오 |

---

## AI 활용

- **Claude Code** — 멱등성 로직 설계, IF Registry + 성능 API 구현, SSE 패턴, Next.js 대시보드 UI
- **Gemini 3.1 Pro** — 금융 도메인 Mock 데이터 생성, PERCENTILE_CONT 쿼리 최적화
- **Antigravity** — FastAPI 재처리 파이프라인, PostgreSQL DDL 자동 생성
