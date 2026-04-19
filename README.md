# IF-Master — Interface Control & Retry Platform

> 보험사 대내외 인터페이스 통합 관제 및 재처리 시스템 (채용 포트폴리오)

**라이브 데모**: [ifmaster.vercel.app](https://ifmaster.vercel.app) — `test_admin / demo1234` 또는 원클릭 데모 버튼

---

## 데모 플로우 (30초)

```
1. 대시보드 접속 → 30초마다 실시간 트랜잭션 자동 생성 (APScheduler + SSE)
2. FAILED 행 클릭 → 우측 슬라이드: Request/Response JSON + Audit Log
3. [재처리] 클릭
   Case A: 외부기관이 이미 처리 → Toast "이미 처리됨 (멱등성 보장)"
   Case B: 미처리 → 재전송 성공 → Toast "재처리 성공"
4. Audit Log 탭에서 실행자·시각 확인
```

---

## 핵심 기능

### 멱등성(Idempotency) 보장

타임아웃으로 실패 기록된 트랜잭션이 실제로는 처리됐을 수 있다. 재처리 전 외부기관에 상태를 먼저 조회해 중복 처리를 방지한다.

```
재처리 요청
    │
    ├─ DB에서 idempotency_key 조회 (SELECT ... FOR UPDATE)
    │
    ├─ GET /mock/status?key={key}
    │   ├─ 이미 처리됨 → DB SUCCESS 업데이트, ALREADY_PROCESSED 반환
    │   └─ 미처리 → POST /mock/call?key={key}
    │               ├─ 성공 → DB SUCCESS, RETRY_SUCCESS audit
    │               └─ 실패 → DB FAILED, retry_count++, RETRY_FAILED audit
    │
    └─ SSE broadcast → 모든 연결 클라이언트에 retry_result 이벤트
```

### 실시간 대시보드

APScheduler가 30초마다 1~3건 트랜잭션을 자동 생성하고, SSE(Server-Sent Events)로 프론트엔드에 즉시 push한다. 빈 화면 없음.

---

## 아키텍처

```
┌─────────────────────────────────┐
│  Frontend (Next.js / Vercel)    │
│  TanStack Table + Recharts      │
│  SSE EventSource (자동 재연결)  │
└────────────┬────────────────────┘
             │ REST + SSE (httpOnly Cookie 인증)
┌────────────▼────────────────────┐
│  Backend (FastAPI / Render)     │
│                                 │
│  /api/stats   → 통계 집계       │
│  /api/logs    → 페이지네이션    │
│  /api/retry   → 멱등성 재처리   │
│  /api/stream  → SSE broadcast   │
│  /mock/*      → 내장 Mock 서버  │
│  APScheduler  → 30초 자동 생성  │
└────────────┬────────────────────┘
             │ asyncpg
┌────────────▼────────────────────┐
│  PostgreSQL (Neon 무료 티어)    │
│  interface_log  (ERD 핵심)      │
│  audit_log      (감사 이력)     │
│  mock_responses (멱등성 저장소) │
└─────────────────────────────────┘
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Frontend | Next.js 15, TanStack Table, Recharts, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), APScheduler |
| Database | PostgreSQL (Neon 무료 티어) |
| 인증 | JWT HS256, httpOnly Cookie |
| 배포 | Vercel (프론트) + Render (백엔드) |
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
- `test_mock_distribution.py` — `/mock/call` 성공률 분포 (45~75%) 검증
- `test_sse_ping.py` — SSE 연결 35초 내 ping 수신 검증

---

## 환경변수 (Render 배포 시)

| 변수 | 설명 |
|------|------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `JWT_SECRET` | 32자 이상 랜덤 문자열 |
| `DEMO_USERNAME` | 데모 계정 아이디 |
| `DEMO_PASSWORD` | 데모 계정 비밀번호 |
| `FRONTEND_URL` | Vercel 배포 URL |
| `COOKIE_SECURE` | `true` (Render HTTPS 환경) |

---

## AI 활용

- **Claude Code** — 멱등성 로직 설계, SSE 패턴, Next.js 대시보드 UI
- **Gemini 3.1 Pro** — 금융 도메인 Mock 데이터 생성, 쿼리 최적화
- **Antigravity** — FastAPI 재처리 파이프라인, PostgreSQL DDL
