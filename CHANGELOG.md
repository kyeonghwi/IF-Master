# Changelog — IF-Master

> Format: [SPEC-ID] Type — Description

---

## [2026-04-24] SPEC-OPS-001 — Operations Enhancement Pack

### feat: Bulk Retry

- `POST /api/retry/bulk` accepts 1–50 log IDs and retries each independently
- Shared `_retry_one` helper extracted from the single-item handler; both paths reuse identical business logic
- Per-item `db.begin()` transactions — a DB error on one item never rolls back committed results for others
- Duplicate log IDs within a request return `ALREADY_PROCESSED` (dedup via `dict.fromkeys`)
- Pydantic `Field(min_length=1, max_length=50)` rejects out-of-range lists before any DB work
- ADMIN/OPERATOR role guard enforced; VIEWER receives HTTP 403
- SSE `retry_result` event emitted per item after each commit
- Route registered before `/{log_id}` to prevent `"bulk"` being parsed as a UUID path parameter
- Frontend: TanStack row-selection column in LogTable; sticky action bar on `logs/page.tsx` with per-item toast summary

### feat: CSV Log Export

- `GET /api/logs/export` streams `text/csv` via async generator + `yield_per(500)` to bound peak memory
- Filter params: `status`, `protocol`, `target_org`, `start_date`, `end_date` (inclusive bounds)
- Hard cap at 10,000 rows; `X-Row-Limit-Reached: true` response header signals truncation
- `Content-Disposition: attachment; filename="if-logs-YYYYMMDD.csv"` using server UTC date
- Null `responded_at` / `response_ms` written as empty CSV cells (REQ-010)
- `_csv_safe()` helper prefixes formula-trigger chars (`= + - @ \t \r`) to prevent spreadsheet injection (CWE-1236)
- Auth required via `get_current_user` dependency; unauthenticated requests → HTTP 401
- Frontend: "Export CSV" button in `logs/page.tsx` header, uses direct navigation with current filter state

### feat: Cron Schedule Validation

- `_validate_cron()` helper in `routers/interfaces.py` applies a 5-field cron regex before `INSERT`/`UPDATE`
- Returns HTTP 422 `{"code": "INVALID_CRON"}` on mismatch; `null`/empty string accepted (no-schedule case)
- Helper text `예: 0 9 * * 1-5` displayed below cron input in `InterfaceFormModal`
- Monospace badge renders cron expression in `interfaces/page.tsx` list view

### Security

- Fixed CSV formula injection (CWE-1236) in log export — all user-controlled string fields sanitized via `_csv_safe`

### Tests

- `backend/tests/test_export.py` — export auth, filter, null cells, X-Row-Limit header, formula injection sanitization
- `backend/tests/test_retry.py` — single-retry backward compatibility, bulk success/partial/forbidden/dedup/empty-list/51-items
