# IF-Master 데모 시나리오 (심사자용)

> 예상 소요시간: 약 3분  
> 접속 URL: https://if-master.vercel.app  
> 테스트 계정: `test_admin` / `demo1234`

---

## 준비사항

1. 브라우저에서 위 URL 접속
2. "데모로 바로 체험하기" 버튼 클릭 → 자동 로그인 (1초 소요)

---

## Step 1 — Control Tower (모니터링)

**메뉴: Control Tower**

- 실시간 트랜잭션 스트림이 30초마다 자동 갱신됨 (SSE)
- 상단 카드: 전체/성공/실패/지연 현황 확인
- 시계열 그래프: 최근 24시간 프로토콜별 처리 추이

**확인 포인트**: 대시보드가 자동으로 살아 움직임 → 운영 시스템 모니터링 재현

---

## Step 2 — Interface Logs (로그 조회)

**메뉴: Interface Logs**

- 기관별 / 프로토콜별 / 상태별 필터 조합 후 조회
- FAILED 상태 로그 클릭 → 슬라이드 패널: Request/Response 전문 + Stack Trace 확인
- "재처리" 버튼 클릭 → 멱등성 시연 (아래 Step 3)

---

## Step 3 — 재처리 + 멱등성 보장 (핵심 비즈니스 로직)

**메뉴: Interface Logs → FAILED 로그 선택**

1. FAILED 상태 로그의 "재처리" 버튼 클릭
2. 시스템이 외부 기관에 실제 처리 여부를 먼저 조회
   - **Case A**: 이미 처리됨 → "중복 처리 방지 (ALREADY_PROCESSED)" 표시
   - **Case B**: 미처리 → Mock 서버 재호출 → SUCCESS/FAILED 결과 반환
3. Audit Log에 처리 이력 기록 (패널 하단 확인)

**확인 포인트**: Idempotency Key 기반 중복 처리 원천 차단 → 금융 시스템 필수 요건

---

## Step 4 — IF Registry (인터페이스 등록·설정·실행)

**메뉴: IF Registry**

- 10개 사전 등록 인터페이스 확인 (REST/SOAP/MQ/BATCH/SFTP 5개 프로토콜)
- "실행" 버튼 클릭 (REST 또는 SOAP 인터페이스 권장)
  - Mock 서버 호출 → 응답시간(ms) + 성공/실패 결과 토스트 표시
  - Control Tower로 이동하면 방금 실행한 로그가 실시간 반영됨 (SSE)
- "+ 신규 등록" → 이름/프로토콜/URL/타임아웃 설정 후 저장 (등록 기능)
- 수정 버튼 → 타임아웃·재시도 설정 변경 (설정 기능)
- 활성/비활성 토글 → 운영 중 인터페이스 긴급 차단

**확인 포인트**: 단일 화면에서 모든 인터페이스 등록·설정·실행 가능

---

## Step 5 — Performance (성능 관리)

**메뉴: Performance**

- SLA 준수율 (목표: 99% / 3000ms 이내)
- 인터페이스별 P95 응답시간 막대 그래프 (빨간 바 = SLA 초과)
- BATCH 프로토콜 → P95 값이 높게 표시됨 (설계 반영: 배치는 5~30초 지연)
- 느린 인터페이스 알림 배너 확인
- 기간 필터: 1h / 6h / 24h / 7d

**확인 포인트**: 프로토콜별 SLA 특성이 데이터에 반영됨 (도메인 지식 코드화)

---

## 커버리지 요약

| 스펙 항목 | 시연 위치 | 핵심 포인트 |
|-----------|-----------|-------------|
| 모니터링 | Control Tower | 실시간 SSE 스트림 |
| 재처리 | Interface Logs | 멱등성 보장 (Idempotency Key) |
| 로그 | Interface Logs | 전문 + Stack Trace |
| 등록 | IF Registry → 신규 등록 | CRUD |
| 설정 | IF Registry → 수정 | 타임아웃·재시도 |
| 실행 | IF Registry → 실행 버튼 | 온디맨드 테스트 |
| 성능 관리 | Performance | P95 / SLA 준수율 |
