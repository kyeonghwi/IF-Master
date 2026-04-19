# Step 4: Next.js 프론트엔드 구현 계획

## 정리 사항 (이전 HTML 접근 작업 제거)

HTML 파일들은 Next.js가 사용하지 않으므로 디자인 목업으로 유지.
단, api.js 스크립트 태그를 추가한 파일들은 정리 필요:
- `health.html`, `settings.html`, `anomalies.html`: script 태그 제거
- `dashboard.html`, `logs.html`: 추가된 script 태그 제거 (정적 목업으로 복원)
- `backend/app/main.py`: StaticFiles 마운트 제거
- `D:/IF-Master/api.js`: 삭제 (Next.js에서 재구현)
- `D:/IF-Master/login.html`: 삭제 (Next.js login 페이지로 대체)

## 기술 스택 (기획서 + 설계문서 원문 그대로)

| 역할 | 기술 |
|------|------|
| Framework | Next.js 15 App Router |
| Styling | Tailwind CSS v3 + CSS custom properties (oklch) |
| Chart | Recharts (AreaChart) |
| Table | TanStack Table v8 |
| UI Components | shadcn/ui (Toast, Badge, Sheet) |
| Data Fetching | TanStack Query v5 |
| HTTP | fetch (native) |
| Font | Barlow Condensed (Google) + Geist Mono (Google) + Pretendard (CDN) |

## 인증 방식 결정

**결정: localStorage JWT**

설계문서 Step 4는 "httpOnly 쿠키"를 언급하지만, Vercel(프론트) + Render(백엔드) 크로스오리진 환경에서 httpOnly 쿠키는 SameSite=None; Secure 설정과 CORS credentials 설정이 필요해 복잡도가 크게 증가. 데모 포트폴리오 목적에 맞게 localStorage Bearer 토큰으로 구현. Next.js middleware에서 쿠키 대신 localStorage 접근 불가 문제 → 로그인 후 클라이언트사이드 redirect로 처리.

## 디렉토리 구조

```
D:/IF-Master/frontend/
├── app/
│   ├── layout.tsx              # Root: Pretendard CDN, fonts, Providers
│   ├── page.tsx                # redirect('/dashboard')
│   ├── globals.css             # CSS 토큰 (oklch), base reset
│   ├── providers.tsx           # QueryClientProvider
│   ├── login/
│   │   └── page.tsx            # 로그인 폼 + 원클릭 데모 버튼
│   └── (main)/
│       ├── layout.tsx          # Sidebar + main wrapper (client, auth guard)
│       ├── dashboard/
│       │   └── page.tsx        # Stats + Chart + Recent Logs + SSE
│       └── logs/
│           └── page.tsx        # Full Log Table + FilterBar + SlidePanel
├── components/
│   ├── Sidebar.tsx             # 사이드바 네비게이션
│   ├── Topbar.tsx              # 상단바 (live dot, clock, actions)
│   ├── StatusBadge.tsx         # FAILED/SUCCESS/PENDING 배지
│   ├── StatsRow.tsx            # 4개 요약 지표 카드
│   ├── TrafficChart.tsx        # Recharts AreaChart (SSE 실시간)
│   ├── ErrorDistTable.tsx      # 오류 분포 미니 테이블
│   ├── RecentLogsTable.tsx     # 대시보드 하단 최근 로그 그리드
│   ├── LogTable.tsx            # 전체 로그 TanStack Table
│   ├── FilterBar.tsx           # 로그 필터 바
│   ├── SlidePanel.tsx          # 로그 상세 슬라이드 패널
│   └── RetryButton.tsx         # 재처리 버튼 (loading/disabled 상태)
├── hooks/
│   ├── useSSE.ts               # EventSource 생명주기 관리
│   └── useAuth.ts              # 토큰 get/set/clear + guardAuth
├── lib/
│   ├── types.ts                # TypeScript 인터페이스 (API 스키마 기반)
│   ├── api.ts                  # authFetch wrapper
│   └── utils.ts                # formatDateTime, formatLatency
├── tailwind.config.ts          # CSS var 기반 색상 토큰
├── next.config.ts              # NEXT_PUBLIC_API_URL 환경변수
├── tsconfig.json
└── package.json
```

## API 엔드포인트 (백엔드 이미 구현)

```
POST /auth/token              { username, password } → { access_token, token_type }
GET  /api/stats               → StatsResponse { total, success, failed, pending, series[] }
GET  /api/logs                ?status=&target_org=&page=1&size=50 → LogsResponse
GET  /api/logs/{id}           → InterfaceLogDetail (+ audit_logs[])
POST /api/retry/{id}          → { result: SUCCESS|FAILED|ALREADY_PROCESSED, message }
GET  /api/stream              SSE: transaction | retry_result | ping 이벤트
```

## 구현 순서 (의존성 기반 순차 실행)

### Phase 1: Foundation (설정 + 공유 코드)
파일: package.json, next.config.ts, tsconfig.json, tailwind.config.ts,
      app/globals.css, app/layout.tsx, app/page.tsx, app/providers.tsx,
      lib/types.ts, lib/api.ts, lib/utils.ts, hooks/useSSE.ts, hooks/useAuth.ts

### Phase 2: Layout + Login (Phase 1 완료 후)
파일: components/Sidebar.tsx, components/Topbar.tsx, components/StatusBadge.tsx
      app/(main)/layout.tsx, app/login/page.tsx

### Phase 3: Dashboard + Logs 페이지 (Phase 2 완료 후, 병렬 가능)
- Agent A: components/StatsRow, TrafficChart, ErrorDistTable, RecentLogsTable
           app/(main)/dashboard/page.tsx
- Agent B: components/LogTable, FilterBar, SlidePanel, RetryButton
           app/(main)/logs/page.tsx

## 디자인 토큰 (HTML 목업에서 추출)

```css
--bg:          oklch(0.12 0.008 75)
--surface:     oklch(0.17 0.008 75)
--surface-2:   oklch(0.22 0.008 75)
--surface-3:   oklch(0.28 0.009 75)
--text:        oklch(0.91 0.008 75)
--text-muted:  oklch(0.58 0.008 75)
--text-dim:    oklch(0.38 0.006 75)
--border:      oklch(0.24 0.006 75)
--accent:      oklch(0.78 0.14 82)      /* amber/gold */
--accent-dim:  oklch(0.78 0.14 82 / 0.12)
--success:     oklch(0.70 0.12 160)
--danger:      oklch(0.65 0.18 28)
--warning:     oklch(0.80 0.13 70)
```

## 환경변수

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

# frontend/.env.production
NEXT_PUBLIC_API_URL=https://{render-app}.onrender.com
```
