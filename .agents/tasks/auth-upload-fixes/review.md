# Review: auth-upload-fixes

## Evidence summary

No git repository exists; no commit messages were available. Python compilation
was run directly (`python -m py_compile`) and all six files passed. All
substantive requirements were verified by reading source files.

---

## Task requirement checks

### 1. library.py — upload restricted to lecturers only

| Check | Result |
|---|---|
| `@roles_required("lecturer")` only on `upload_file` (line 69) | ✅ |
| No `institution_admin` / `super_admin` in upload decorator | ✅ |
| Super-admin institution_id form logic removed | ✅ — no such code present |
| `institution_id = user.institution_id` set unconditionally (line 73) | ✅ |

### 2. library.js — canUpload restricted to lecturers only

| Check | Result |
|---|---|
| `canUpload = () => state.user && state.user.role === "lecturer"` (line 7) | ✅ |
| `UPLOAD_ROLES` constant absent | ✅ |
| Super-admin institution picker absent from `openUploadModal` | ✅ |
| `buildModal([])` called directly with no `isSuperAdmin` branch (line 239) | ✅ |

### 3. Backend GET endpoints — optional JWT

| File / Endpoint | Decorator | `get_jwt_identity` imported |
|---|---|---|
| `library.py list_files` | `@jwt_required(optional=True)` | ✅ |
| `library.py download_file` | `@jwt_required(optional=True)` | ✅ |
| `marketplace.py list_items` | `@jwt_required(optional=True)` | ✅ |
| `lostandfound.py list_items` | `@jwt_required(optional=True)` | ✅ |
| `announcements.py list_announcements` | `@jwt_required(optional=True)` | ✅ |
| `community.py list_posts` | `@jwt_required(optional=True)` | ✅ |
| `community.py get_post` | `@jwt_required(optional=True)` | ✅ |

Unauthenticated guests supply `?institution_id=` via query param; authenticated
users get institution_id from token. Both paths verified in source.

### 4. app.js — guest / public access

| Check | Result |
|---|---|
| `init()` routes to `"library"` when no token (not login) | ✅ |
| `renderTopBar()` shows Login + Register when `!state.user` | ✅ |
| `buildNav()` renders guest-only tabs when `!state.user` | ✅ |
| `requireLogin` exported | ✅ |
| `router()` guards dashboard, timetable, assignments, admin | ✅ |

### 5. marketplace.js and lostandfound.js — requireLogin for write actions

| File | Import | Call site |
|---|---|---|
| `marketplace.js` | imports `requireLogin` from `./app.js` (line 4) | `if (!requireLogin("post a listing", true)) return;` (line 38) |
| `lostandfound.js` | imports `requireLogin` from `./app.js` (line 4) | `if (!requireLogin("post a lost/found item", true)) return;` (line 38) |

### 6. Python compilation

```
python -m py_compile app/library.py       → exit 0
python -m py_compile app/marketplace.py   → exit 0
python -m py_compile app/lostandfound.py  → exit 0
python -m py_compile app/announcements.py → exit 0
python -m py_compile app/community.py     → exit 0
python -m py_compile app/auth.py          → exit 0
```

---

## Blockers

None.

---

## Verdict

**APPROVED** — all task requirements are implemented correctly. No correctness,
security, or data failures introduced.
