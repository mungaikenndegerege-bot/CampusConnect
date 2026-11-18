# Review: Optional Accounts, Rate Limiting, Content Reporting, Admin Moderation

## Verification method
Diff read via `git diff HEAD~1..HEAD`. All changed files read in full. Python files spot-compiled (exit 0). Commit message contains only the feature summary; no recorded py_compile output — compilation confirmed by spot-check in this review.

---

## Requirement coverage

| # | Requirement | Status |
|---|-------------|--------|
| 1 | `Account`, `AccountSession`, `Report` models in `app/models.py` | ✅ |
| 2 | `app/ratelimit.py` — in-memory limiter, `check_rate_limit(max, window)` decorator | ✅ |
| 3 | `accounts_bp` with register/login/me/update/logout; token = uuid hex; 30-day expiry; validation rules | ✅ |
| 4 | `POST /api/report` (10/hr), `POST /api/posts` (5/hr), `POST /api/marketplace` (3/hr), `POST /api/lostandfound` (5/hr) | ✅ |
| 5 | `GET /api/admin/reports` (unresolved, with preview), `POST /api/admin/reports/<id>/resolve` | ✅ |
| 6 | `accounts_bp` registered in `app/__init__.py` | ✅ |
| 7 | `renderAccountBar`, `openAccountModal`, login/register tabs, `openReportModal`, `submitReport` in `account.js` | ✅ |
| 8 | `account-bar` div in `<header>`, `account.js` script tag in `index.html` | ✅ |
| 9 | 🚩 Report button on `renderPostCard`, `renderMarketCard`, `renderLFCard` in `feed.js` | ✅ |
| 10 | Reports tab in `admin.js` with Delete Content / Dismiss buttons | ✅ |

---

## Security and correctness checks

**Admin guard on report endpoints** — `list_reports` and `resolve_report` both call `require_admin()` before acting. ✅

**Rate limiter correctness** — `_hits` keyed by `(ip, endpoint)`. Lock used correctly. Sliding window implemented via list-filter before count check. ✅

**Token expiry** — `_get_account` applies a 30-day cutoff against `AccountSession.created_at`. Matches the `SESSION_DAYS = 30` constant. ✅

**Password hashing** — `generate_password_hash` / `check_password_hash` from werkzeug. ✅

**Registration validation** — name 2–100 chars, email regex, password ≥ 8 chars, duplicate email check returning 409. ✅

**XSS in `openReportModal`** — `contentType` is a hardcoded string literal at every call site (`'post'`, `'marketplace'`, `'lostandfound'`) and is additionally escaped via `escHtml`. `contentId` is an integer field (`p.id`, `m.id`, `l.id`) from the API, interpolated as a bare number. No XSS path. ✅

**Report button / card navigation conflict** — `feed.js` line 26 guards the card click handler with `e.target.closest('button, a')`. Each report button also calls `event.stopPropagation()`. Both defences in place. ✅

**`escHtml` availability in `account.js`** — defined in `app.js`, which is loaded before `account.js` in `index.html`. ✅

**`content_type` server-side validation** — `create_report` checks the value is in `('post', 'marketplace', 'lostandfound')` before inserting. ✅

**Reporter IP stored, not leaked publicly** — `reporter_ip` is exposed only via the admin-guarded `/api/admin/reports` endpoint. ✅

---

## Non-blocking observations (out of scope)

- `submitReport` catches only network-level `fetch` exceptions, so a 429 rate-limit response silently shows a generic error toast rather than the server's error message. Consistent with how the rest of the codebase handles errors; not a correctness or security failure.
- `Report.reason` is a `String(200)` column but no server-side length cap is enforced. The task spec does not require one; the fixed `<select>` in the UI ensures values are short in practice.

---

## Verdict

**APPROVED** — all ten requirements are met, all Python files compile, the blueprint is registered, rate limits match the specified routes and limits, admin endpoints are guarded, and no correctness, security, or data failures were found in the changed paths.
