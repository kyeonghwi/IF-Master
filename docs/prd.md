# PRD — IF-Master 설계 의도 및 기술 결정

> 작성일: 2026-04-20  
> 대상: 코드 리뷰어, 채용 심사자

---

## 1. 왜 이 시스템을 만들었나

보험사는 금감원, 결제대행사, 제휴 대리점 등 수십 개 외부 기관과 REST, SOAP, MQ, BATCH, SFTP 등 이종 프로토콜로 연동된다. 장애 발생 시 각 시스템의 로그를 개별 조회해야 해서 MTTR(평균 복구 시간)이 길어진다.

**핵심 문제 두 가지:**

1. **가시성 부재** — 어떤 인터페이스가 지금 살아있는지, 어디서 실패했는지 한 화면으로 볼 수 없다.
2. **안전한 재처리 불가** — 타임아웃 실패 트랜잭션을 재처리할 때 외부 기관이 이미 처리했다면 중복 실행(이중 출금, 이중 보고)이 된다. 금융 시스템에서 이는 규제 위반이다.

---

## 2. 무엇을 만들었나 (기능 범위)

| 기능 | 선택 이유 |
|------|-----------|
| **통합 모니터링** | 첫 번째 문제 직접 해결. 단일 화면에서 전체 인터페이스 상태 파악 |
| **원클릭 재처리 (멱등성 보장)** | 두 번째 문제 직접 해결. 포트폴리오에서 가장 차별화되는 비즈니스 로직 |
| **IF Registry + 온디맨드 실행** | "등록·설정·실행"을 커버해야 관리 시스템으로 완성됨 |
| **성능 관리 (P95/SLA)** | 운영 지표 없이는 관제 시스템이 아님. 프로토콜별 병목 식별 가능 |
| **통합 로그 조회** | 분산 로그를 단일 테이블에서 조회 — 운영 실무에서 가장 많이 쓰는 기능 |

포함하지 않은 것:
- 실제 외부 기관 연동 (채용 포트폴리오 범위 초과, Mock으로 대체)
- 스케줄러 UI (schedule_cron 컬럼만 확보, 구현은 v2 범위)
- 알림/Alert 발송 (느린 인터페이스 감지만 구현)

---

## 3. 핵심 설계 결정

### 3-1. 멱등성 설계

**문제:** 타임아웃으로 실패한 트랜잭션은 외부 기관에서 이미 처리됐을 수 있다.  
**해결:** 재처리 전 외부 기관에 상태를 먼저 조회한다.

```
재처리 요청
    │
    ├─ SELECT ... FOR UPDATE  ← 동시 재처리 방지 (비관적 잠금)
    │
    ├─ GET /mock/status?key={idempotency_key}
    │   ├─ 이미 처리됨 → DB SUCCESS, ALREADY_PROCESSED 반환
    │   └─ 미처리 → POST /mock/call?key={key}
    │
    └─ AuditLog 기록 (실행자, 시각, 결과)
```

**idempotency_key 형식:** `{대상기관[:6]}-{yyyyMMdd}-{uuid8}`  
예: `금감원-20260420-a3f7c291`

`SELECT ... FOR UPDATE`로 동시에 두 명이 같은 트랜잭션을 재처리하는 Race Condition을 방지한다.

---

### 3-2. 온디맨드 실행 vs. HTTP 내부 호출

**초안:** `POST /interfaces/{id}/execute` → 내부적으로 `httpx`로 `/mock/call` 호출  
**문제:** 같은 프로세스 내 루프백 HTTP 호출은 불필요한 소켓 오버헤드 + 추적 어려움  
**결정:** `mock_service.dispatch()` 함수를 직접 호출. 비동기 함수 호출로 오버헤드 제거.

```python
# 채택: 직접 함수 호출
outcome, response_ms, response_json = await mock_service.dispatch(
    key=idempotency_key, protocol=cfg.protocol, timeout_ms=cfg.timeout_ms, db=db
)
```

---

### 3-3. Mock 서버 프로토콜 분기

각 프로토콜은 실제 운영 환경에서 응답 특성이 다르다. 단일 랜덤 응답은 성능 데이터를 왜곡한다.

| 프로토콜 | 응답 범위 | 성공률 | 근거 |
|----------|-----------|--------|------|
| REST | 200~1,500ms | 70% | HTTP REST API 표준 응답 |
| SOAP | 500~3,000ms | 65% | XML 파싱 + 레거시 시스템 |
| MQ | 100~500ms | 85% | 큐 기반 비동기 ACK |
| BATCH | 5,000~30,000ms | 80% | 대량 데이터 처리 지연 |
| SFTP | 1,000~5,000ms | 75% | 파일 전송 오버헤드 |

timeout_ms를 초과하면 즉시 FAILED 처리 — 설정값이 실제 동작에 반영된다.

---

### 3-4. SSE vs. WebSocket

**선택:** SSE (Server-Sent Events)  
**이유:**
- 재처리 결과·실행 결과를 클라이언트에 push하는 단방향 스트림으로 충분하다.
- WebSocket은 양방향이 필요할 때 쓴다. 여기서는 서버 → 클라이언트 단방향.
- SSE는 HTTP 위에 동작해 Vercel/Render 프록시 통과가 쉽고, 자동 재연결이 브라우저 표준으로 내장돼 있다.

---

### 3-5. 성능 집계: PERCENTILE_CONT vs. 애플리케이션 계산

**선택:** PostgreSQL `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms)`  
**이유:**
- P95/P99를 애플리케이션에서 계산하려면 전체 response_ms를 메모리에 올려야 한다.
- PostgreSQL 집계 함수는 인덱스 없이도 정렬 집계를 서버 내에서 처리한다. 행이 수만 건이어도 단일 쿼리로 해결.

---

### 3-6. 인증: JWT + httpOnly Cookie

**선택:** JWT HS256, httpOnly Cookie 전송  
**이유:**
- `localStorage`에 토큰 저장 시 XSS로 탈취 가능.
- httpOnly Cookie는 JavaScript에서 접근 불가 → XSS 방어.
- SameSite=Lax로 CSRF 위험 완화.
- Vercel(프론트)과 Render(백엔드) 도메인이 달라 `SameSite=None; Secure` 적용.

---

## 4. 기술 스택 선택 근거

### Python / FastAPI vs. Spring Boot

| 기준 | FastAPI | Spring Boot |
|------|---------|-------------|
| 프로토타입 속도 | 빠름 (타입힌트 → 자동 스키마) | 느림 (설정·보일러플레이트) |
| 비동기 지원 | 네이티브 (async/await) | WebFlux 필요 |
| 금융 도메인 채택 | 데이터 분석·자동화에 Python 증가 | 엔터프라이즈 전통 강함 |
| AI 코드 생성 품질 | Claude/Gemini 최적화 잘 됨 | 구조 복잡해 생성 품질 편차 |

**결론:** 프로토타입 + 바이브코딩 환경에서 FastAPI가 3배 이상 빠르다.

### PostgreSQL vs. SQLite

SQLite는 동시 쓰기에 테이블 락이 걸린다. APScheduler가 30초마다 자동 생성하는 트랜잭션 + 사용자 재처리 + SSE 브로드캐스트가 동시에 발생하는 구조에서 SQLite는 한계가 있다. PostgreSQL의 MVCC가 이 부분을 해결한다.

### Render vs. Heroku

2022년 Heroku 무료 플랜 종료. Render가 FastAPI 컨테이너 + PostgreSQL 무료 티어를 같은 플랫폼에서 제공한다.

---

## 5. 아키텍처 선택: 모노레포 vs. 분리 레포

**선택:** 모노레포 (단일 `IF-Master` 레포, `frontend/` + `backend/` 서브디렉토리)  
**이유:** 포트폴리오 프로젝트는 한 레포에서 전체 코드를 보여주는 게 심사자 편의 측면에서 낫다. 배포는 Vercel(프론트)/Render(백엔드)로 독립적으로 가능하므로 단점이 없다.

---

## 6. 하지 않은 것과 이유

| 항목 | 하지 않은 이유 |
|------|---------------|
| Alembic 마이그레이션 | `create_all`이 자동으로 처리. 프로토타입에서 마이그레이션 관리 오버헤드 불필요 |
| 도커 컴포즈 프로덕션 | Render가 컨테이너 관리. 로컬 개발용만 유지 |
| Redis 캐시 | 트래픽 규모가 Render 무료 인스턴스 수준. 지금 Redis를 도입할 이유 없음 |
| E2E 테스트 (Playwright) | 단위/통합 테스트로 API 동작 검증 충분. 브라우저 자동화는 과잉 |
| PII 마스킹 실제 구현 | 시드 데이터에 실제 개인정보 없음. 설계 명세만 문서화 |
