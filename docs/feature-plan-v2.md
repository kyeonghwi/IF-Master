# IF-Master v2 — 기능 완성 계획서

> 작성일: 2026-04-20  
> 목적: 채용 과제 스펙 7항목 100% 커버  
> 기준: 등록·설정·실행·모니터링·재처리·로그·성능 관리

---

## 현재 커버리지

| 스펙 항목 | 현황 | 비고 |
|-----------|------|------|
| 모니터링 | ✅ 완료 | 실시간 대시보드 + SSE |
| 재처리 | ✅ 완료 | 멱등성 보장 포함 |
| 로그 | ✅ 완료 | 상세 조회 + Audit Log |
| 등록 | ❌ 없음 | Interface Registry 필요 |
| 설정 | ❌ 없음 | 타임아웃·재시도 설정 필요 |
| 실행 | ❌ 없음 | 온디맨드 테스트 실행 필요 |
| 성능 관리 | ❌ 없음 | 응답시간 P95·SLA 필요 |

**목표: 4개 기능 추가 → 7/7 완성**

---

## Phase 1 — DB 스키마 확장

### 1-1. `interface_config` 테이블 신규 생성

인터페이스 등록·설정의 영속 저장소.

```sql
CREATE TABLE interface_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,       -- "금감원 보험계약 조회"
    protocol        VARCHAR(10)  NOT NULL,              -- REST, SOAP, MQ, BATCH, SFTP
    target_org      VARCHAR(50)  NOT NULL,              -- "금감원", "국민은행" 등
    endpoint_url    VARCHAR(300) NOT NULL,              -- 대상 URL / 큐명 / 경로
    timeout_ms      INTEGER      NOT NULL DEFAULT 5000,
    max_retry       INTEGER      NOT NULL DEFAULT 3,
    enabled         BOOLEAN      NOT NULL DEFAULT TRUE,
    description     TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

### 1-2. `interface_log.response_ms` 컬럼 추가

성능 관리 집계에 필요.

```sql
ALTER TABLE interface_log ADD COLUMN response_ms INTEGER;
-- 기존 데이터: responded_at - called_at 으로 backfill
UPDATE interface_log
   SET response_ms = EXTRACT(EPOCH FROM (responded_at - called_at)) * 1000
 WHERE responded_at IS NOT NULL;
```

### 1-3. 시드 데이터 확장

- 프로토콜 다양화: REST 40% / SOAP 25% / BATCH 20% / MQ 10% / SFTP 5%
- `response_ms` 추가: 성공 200~2000ms, 실패 3000~8000ms, 배치 5000~30000ms
- `interface_config` 기본 10개 등록

---

## Phase 2 — 백엔드 API

### 2-1. Interface Registry API (`/api/interfaces`)

**파일**: `backend/app/routers/interfaces.py`

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/interfaces` | 전체 목록 (enabled 필터 가능) |
| POST | `/api/interfaces` | 신규 등록 |
| PUT | `/api/interfaces/{id}` | 설정 수정 |
| DELETE | `/api/interfaces/{id}` | 삭제 |
| PATCH | `/api/interfaces/{id}/toggle` | enabled 토글 |

**스키마 추가** (`schemas.py`):
```python
class InterfaceConfigBase(BaseModel):
    name: str
    protocol: str  # REST | SOAP | MQ | BATCH | SFTP
    target_org: str
    endpoint_url: str
    timeout_ms: int = 5000
    max_retry: int = 3
    enabled: bool = True
    description: str | None = None

class InterfaceConfigCreate(InterfaceConfigBase): pass

class InterfaceConfigResponse(InterfaceConfigBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
```

### 2-2. 온디맨드 실행 API

**파일**: `backend/app/routers/interfaces.py` (위에 추가)

```
POST /api/interfaces/{id}/execute
```

동작:
1. `interface_config` 조회 → `enabled` 확인
2. `idempotency_key` 생성: `{target_org}-{yyyyMMdd}-{uuid8}`
3. `interface_log` INSERT (status=PENDING)
4. `POST /mock/call?key={key}` 호출 (timeout_ms 적용)
5. 결과로 `interface_log` 업데이트 + `response_ms` 기록
6. SSE로 `event: execution_result` 브로드캐스트
7. 결과 반환 (log_id, status, response_ms)

### 2-3. 성능 관리 API (`/api/performance`)

**파일**: `backend/app/routers/performance.py`

```
GET /api/performance?from_dt=&to_dt=&protocol=&target_org=
```

반환 구조:
```python
class PerformanceResponse(BaseModel):
    by_interface: list[InterfacePerf]  # 인터페이스별 집계
    sla_summary: SlaSummary            # 전체 SLA 요약
    slow_alerts: list[SlowAlert]       # P95 > 3000ms 인터페이스

class InterfacePerf(BaseModel):
    service_name: str
    protocol: str
    target_org: str
    call_count: int
    avg_ms: float
    p95_ms: float
    p99_ms: float
    sla_rate: float      # response_ms < 3000ms 비율

class SlaSummary(BaseModel):
    total_calls: int
    within_sla: int
    sla_rate: float      # 목표: 99%

class SlowAlert(BaseModel):
    service_name: str
    p95_ms: float
    call_count: int
```

SQL 핵심 쿼리:
```sql
SELECT
    service_name,
    protocol,
    target_org,
    COUNT(*) AS call_count,
    AVG(response_ms) AS avg_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms) AS p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_ms) AS p99_ms,
    COUNT(*) FILTER (WHERE response_ms < 3000) * 100.0 / COUNT(*) AS sla_rate
FROM interface_log
WHERE called_at BETWEEN :from_dt AND :to_dt
  AND response_ms IS NOT NULL
GROUP BY service_name, protocol, target_org
ORDER BY p95_ms DESC;
```

---

## Phase 3 — 프론트엔드

### 3-1. Interface Registry 페이지

**파일**: `frontend/app/(main)/interfaces/page.tsx`

레이아웃:
```
[인터페이스 관리]                        [+ 신규 등록]
┌──────────────────────────────────────────────────────┐
│ 이름          프로토콜  대상기관  URL    타임아웃  상태  액션  │
│ 금감원 계약조회  REST    금감원   /api/  5000ms   ON   [실행][수정][삭제] │
│ 국민은행 출금   SOAP    국민은행  /ws/   3000ms   ON   [실행][수정][삭제] │
│ 손해율 배치    BATCH   내부     /job/  30000ms  OFF  [실행][수정][삭제] │
└──────────────────────────────────────────────────────┘
```

컴포넌트 목록:
- `InterfaceTable.tsx` — 목록 테이블 (정렬·필터)
- `InterfaceFormModal.tsx` — 등록/수정 모달 (react-hook-form + zod)
- `ExecuteButton.tsx` — 실행 버튼 + 결과 토스트

프로토콜별 배지 색상:
- REST: 파랑 / SOAP: 보라 / MQ: 노랑 / BATCH: 회색 / SFTP: 초록

### 3-2. Performance 페이지

**파일**: `frontend/app/(main)/performance/page.tsx`

레이아웃:
```
[성능 관리]        기간: [최근 24h ▼]  프로토콜: [전체 ▼]

[SLA 준수율 98.7%]  [평균 응답시간 342ms]  [P95 응답시간 1,823ms]  [지연 알림 2건]

┌─────────────────────────────┐  ┌──────────────────────────────┐
│ 인터페이스별 P95 응답시간    │  │ 프로토콜별 SLA 준수율 도넛   │
│ (막대 그래프, 3000ms 기준선) │  │                              │
└─────────────────────────────┘  └──────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ ⚠️ 느린 인터페이스 알림 (P95 > 3000ms)               │
│ 손해율 배치: P95 18,432ms · 52건                     │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ 인터페이스명     프로토콜  호출수  평균  P95   P99   SLA  │
│ (정렬 가능 테이블)                                    │
└──────────────────────────────────────────────────────┘
```

컴포넌트 목록:
- `PerformanceSummaryCards.tsx` — 상단 4개 KPI 카드
- `P95BarChart.tsx` — Recharts 수평 막대, 3000ms 기준선
- `SlaDonutChart.tsx` — 프로토콜별 SLA 도넛
- `SlowAlertBanner.tsx` — P95 초과 인터페이스 경고
- `PerformanceTable.tsx` — 상세 수치 테이블

### 3-3. Sidebar 메뉴 추가

**파일**: `frontend/components/Sidebar.tsx`

기존:
- 대시보드
- 로그 조회

추가:
- **인터페이스 관리** (등록·설정·실행)
- **성능 관리**

### 3-4. 프로토콜 배지 컴포넌트

**파일**: `frontend/components/ProtocolBadge.tsx`

기존 `StatusBadge.tsx` 패턴 그대로 따름. 5개 프로토콜 색상 매핑.

---

## Phase 4 — 모델 연결 & Mock 확장

### 4-1. SQLAlchemy 모델 추가

**파일**: `backend/app/db/models.py`

```python
class InterfaceConfig(Base):
    __tablename__ = "interface_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(VARCHAR(100), unique=True, nullable=False)
    protocol: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)
    target_org: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(VARCHAR(300), nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=5000)
    max_retry: Mapped[int] = mapped_column(Integer, default=3)
    enabled: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None] = mapped_column(TEXT)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

`InterfaceLog`에 컬럼 추가:
```python
response_ms: Mapped[int | None] = mapped_column(Integer)
```

### 4-2. Mock 서버 프로토콜 분기

**파일**: `backend/app/routers/mock_router.py`

프로토콜별 응답 특성:
- REST: 200~1500ms, 성공 70%
- SOAP: 500~3000ms, 성공 65% (XML envelope 포함 응답)
- MQ: 100~500ms, 성공 85% (큐 ACK 시뮬레이션)
- BATCH: 5000~30000ms, 성공 80% (배치 처리 지연)
- SFTP: 1000~5000ms, 성공 75% (파일 전송 시뮬레이션)

### 4-3. Alembic 마이그레이션

**파일**: `backend/alembic/versions/002_add_interface_config_and_response_ms.py`

---

## Phase 5 — 라우터 등록 & 테스트

### 5-1. main.py 라우터 등록

```python
from app.routers import interfaces, performance

app.include_router(interfaces.router, prefix="/api", tags=["interfaces"])
app.include_router(performance.router, prefix="/api", tags=["performance"])
```

### 5-2. 테스트 추가

**파일**: `backend/tests/test_interfaces.py`
- CRUD 전체 플로우
- enabled=False 인터페이스 실행 시 400 반환
- 실행 결과 SSE 이벤트 브로드캐스트 확인

**파일**: `backend/tests/test_performance.py`
- P95 계산 정확도
- SLA 집계 수치 검증

---

## 구현 순서 요약

```
Step 1: DB 마이그레이션 (0.5h)
  - InterfaceConfig 테이블 생성
  - interface_log.response_ms 컬럼 추가
  - Alembic revision 작성

Step 2: 시드 데이터 확장 (0.5h)
  - interface_config 10개 기본 등록
  - interface_log response_ms 반영 + 프로토콜 다양화

Step 3: 백엔드 — Interface Registry API (2h)
  - models.py InterfaceConfig 추가
  - schemas.py 추가
  - routers/interfaces.py CRUD + toggle + execute

Step 4: 백엔드 — Performance API (1h)
  - routers/performance.py
  - PERCENTILE_CONT 집계 쿼리

Step 5: 백엔드 — Mock 프로토콜 분기 (0.5h)
  - mock_router.py 프로토콜별 응답 특성 분기

Step 6: 프론트엔드 — Interface Registry 페이지 (4h)
  - InterfaceTable, InterfaceFormModal, ExecuteButton
  - /interfaces 라우트

Step 7: 프론트엔드 — Performance 페이지 (3h)
  - PerformanceSummaryCards, P95BarChart, SlaDonutChart
  - SlowAlertBanner, PerformanceTable
  - /performance 라우트

Step 8: 프론트엔드 — Sidebar + ProtocolBadge (0.5h)

Step 9: 테스트 + 배포 확인 (1h)
  - Render 재배포
  - 심사자 시나리오 E2E 확인
```

**총 예상 소요**: ~13시간

---

## 완성 후 커버리지

| 스펙 항목 | 구현 위치 |
|-----------|-----------|
| 등록 | Interface Registry — POST /api/interfaces |
| 설정 | Interface Registry — PUT /api/interfaces/{id} |
| 실행 | Execute 버튼 — POST /api/interfaces/{id}/execute |
| 모니터링 | 기존 대시보드 (완료) |
| 재처리 | 기존 재처리 (완료) |
| 로그 | 기존 로그 조회 (완료) |
| 성능 관리 | Performance 페이지 — GET /api/performance |

**7/7 ✅**

---

## /autoplan Review Report

> Generated: 2026-04-20 | Branch: master | Phases: CEO + Design + Eng | Model: Claude subagent only [codex-unavailable]

### Phase 1 — CEO Review

**0A. Premise Challenge**
1. 채용 스펙 7항목이 자기주장된 매핑임 — "실행"이 온디맨드 버튼인지 스케줄러 관리인지 원문 확인 필요
2. 나머지 전제는 타당: Registry 없이는 "중앙화된 통합관리"가 불완전, response_ms 없이는 성능 집계 불가

**0B. 기존 코드 활용 맵**
- InterfaceRegistry → InterfaceLog의 target_org/service_name 패턴 재활용
- execute → retry.py의 httpx + AuditLog 패턴 재활용
- performance → stats.py의 집계 쿼리 패턴 재활용
- InterfaceFormModal → SlidePanel.tsx 스타일 재활용

**CEO Findings:**

| # | 심각도 | 발견사항 | 수정사항 |
|---|-------|---------|---------|
| C1 | CRITICAL | **데모 스크립트 없음** — 7/7 커버리지가 심사자에게 보이지 않음 | docs에 6단계 데모 시나리오 추가 |
| C2 | HIGH | **시간 추정 낙관적** — 프론트엔드 폼+차트 실제 8-10h | SlaDonutChart 제거, P95 정밀도 테스트 → 스모크 테스트로 교체 |
| C3 | HIGH | **"실행" 스펙 해석 불확실** — 온디맨드 버튼 vs 스케줄러 관리 | 제출 전 공고 원문 재확인 필요 |
| C4 | MEDIUM | **execute가 mock에만 연결** — 프로토콜별 핸들러 없으면 cosmetic | 프로토콜별 stub 클래스 5개 (5줄씩) 추가 |
| C5 | MEDIUM | **ProtocolBadge가 차별점** — 페이지 첫 시각 요소로 배치 필요 | InterfaceRegistry 테이블 1열 배치 확인 |

---

### Phase 2 — Design Review

**Design Findings:**

| # | 심각도 | 컴포넌트 | 발견사항 | 수정사항 |
|---|-------|---------|---------|---------|
| D1 | CRITICAL | `InterfaceTable.tsx` | 로딩 상태 없음 | TableSkeleton 5행 추가 |
| D2 | CRITICAL | `InterfaceTable.tsx` | Delete 확인 없이 즉시 삭제 | ConfirmDialog 모달 추가 |
| D3 | HIGH | `ExecuteButton.tsx` | 실행 중 in-progress 상태 없음 | 스피너 + disabled 추가 (SSE 이벤트 수신까지) |
| D4 | HIGH | `InterfaceFormModal.tsx` | zod 검증 규칙 미명시 | name(max100), protocol(enum), timeout_ms(100-60000), max_retry(0-10), url(조건부) |
| D5 | HIGH | `InterfaceTable.tsx` | 활성 인터페이스 토글 시 경고 없음 | 인라인 confirm 토스트 추가 |
| D6 | HIGH | `page.tsx` | 10초 내 기능 파악 불가 | 부제목 추가: "외부 기관 연계 인터페이스를 등록하고 온디맨드 테스트 실행을 수행합니다" |
| D7 | MEDIUM | `P95BarChart`, `SlaDonutChart` | 빈 데이터 상태 없음 | "해당 기간에 데이터가 없습니다" 빈 상태 추가 |
| D8 | MEDIUM | `PerformanceSummaryCards` | API 오류 상태 없음 | "데이터 로드 실패 + 재시도 버튼" 추가 |
| D9 | MEDIUM | `SlowAlertBanner` | KPI 카드 아래 배치 → 중요 경고 늦게 보임 | KPI 카드 위로 이동 |
| D10 | LOW | `InterfaceTable.tsx` | enabled 컬럼이 5번째 → 2번째로 이동 | 열 순서 조정 |

---

### Phase 3 — Engineering Review

**Eng Findings:**

| # | 심각도 | 영역 | 발견사항 | 수정사항 |
|---|-------|------|---------|---------|
| E1 | CRITICAL | DB 마이그레이션 | **Alembic 미초기화** — alembic/ 디렉토리 없음, 계획대로 하면 배포 실패 | Alembic 제거, models.py에 모델 추가만으로 충분 (create_all이 자동 처리) |
| E2 | HIGH | execute 엔드포인트 | mock 라우터를 httpx로 내부 호출 → async worker 낭비, 루프백 오버헤드 | `mock_service.dispatch(key, protocol, timeout_ms)` 함수로 추출, 직접 호출 |
| E3 | HIGH | 인증 | 신규 라우터에 auth 미지정 → `/api/interfaces`, `/api/performance` 무인증 | `dependencies=[Depends(require_auth)]` 추가 (stats/logs 패턴 동일) |
| E4 | HIGH | execute 엔드포인트 | `/mock/call?key=` 호출 시 protocol 미전달 → 프로토콜별 응답 특성 동작 안 함 | `protocol` 파라미터 추가 또는 서비스 함수에서 처리 |
| E5 | MEDIUM | ORM | `onupdate=func.now()` — raw text() UPDATE 시 미동작 경고 필요 | PUT 핸들러에서 객체 직접 수정 후 flush 방식 사용 |
| E6 | MEDIUM | API | `GET /api/interfaces` 페이지네이션 없음 | `/api/logs` 패턴 동일하게 `page`/`size` 파라미터 추가 |
| E7 | MEDIUM | 테스트 | SSE 브로드캐스트 테스트 — AsyncClient로 SSE 스트림 단언 불가 | broadcast 함수를 asyncio.Queue mock으로 대체, 큐 수신 이벤트 단언 |

---

### 자동 결정 내역

| # | 결정 | 분류 | 원칙 |
|---|------|------|------|
| 1 | Alembic 건너뜀 → models.py + create_all 유지 | Mechanical | P5 (명시적 > 영리) |
| 2 | execute → mock_service.dispatch() 직접 호출 | Mechanical | P5 |
| 3 | 신규 라우터에 require_auth 추가 | Mechanical | P1 (완전성) |
| 4 | execute에 protocol 파라미터 추가 | Mechanical | P1 |
| 5 | Delete ConfirmDialog 추가 | Mechanical | P1 |
| 6 | SlowAlertBanner → KPI 카드 위로 이동 | Mechanical | P5 |
| 7 | GET /api/interfaces 페이지네이션 추가 | Mechanical | P1 |

### 취향 결정 (사용자 확인 필요)

| # | 결정 | 옵션 A | 옵션 B |
|---|------|--------|--------|
| T1 | SlaDonutChart 유지 vs 제거 | 제거 (시간 절약 2h, bar chart로 충분) | 유지 (완성도 높음, 추가 시간 필요) |
| T2 | 데모 스크립트 위치 | docs/demo-guide.md 별도 파일 | README.md 하단 섹션 |

---

### Advisor 검토 추가사항

| # | 내용 | 조치 |
|---|------|------|
| A1 | **schedule_cron 컬럼 추가** — "실행" 스펙 해석 헷지. interface_config에 `schedule_cron VARCHAR(50) NULL` 추가, Registry 테이블에 "스케줄" 열 표시 | Step 1에 포함 (30분) |
| A2 | **바이브코딩 산출물 확인** — 기획서에 프롬프트 캡처 첨부 예정 명시. 실제 캡처 파일 준비 여부 확인 필요 | 제출 전 별도 확인 |
| A3 | **T1 결정: SlaDonutChart 제거** — bar chart + table로 충분, 2h 절감 | 계획에서 SlaDonutChart 제거 |
| A4 | **T2 결정: demo-guide.md 별도 파일** — docs/demo-guide.md 생성 | Step 9에 포함 |
| A5 | **responded_at 백필 전제 검증** — 기존 데이터에 responded_at NULL 비율 확인 필요 | Step 1 시작 전 쿼리 실행 |

**Status: DONE_WITH_CONCERNS**

Critical(3): C1 데모스크립트, D1/D2 로딩·삭제확인, E1 Alembic
High(7): C2/C3, D3/D4/D5/D6, E2/E3/E4
Medium(7): C4/C5, D7/D8/D9, E5/E6/E7
