# Kenyan institution directory and community grouping system

This change adds a searchable directory of 207 Kenyan educational institutions (public universities, private universities, university colleges, national polytechnics, TTIs, TVETs, and specialised institutions) to CampusConnect, with an auto-created community for every institution. Users can select a home institution stored in `localStorage`, browse other institutions' communities, and post to them without creating an account. Administrators get a full management tab: add, edit, deactivate, and CSV-import institutions. Five new SQLAlchemy models back the feature; they are appended to `app/models.py` without touching any existing model. Build verification (py_compile + seed run + Flask startup) passed and is recorded in the commit message.

**Watch for:** The FAB button wiring in `navigate()` registers an `openPostForm('institutions')` handler that silently does nothing — confirmed dead code that breaks the global FAB on the directory landing page. The seed contains one duplicate institution name and five reused abbreviations that the dedup logic only partially catches. `member_count` is never incremented, so the "popular institutions" sort and all member counts are permanently zero.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The five new models form a clean chain: `InstitutionCategory → Institution → InstitutionCommunity → InstitutionPost → InstitutionPostComment`. All have `to_dict()` methods and correct FK relationships. No existing model is altered.

The API surface is split across two blueprints — `institutions_bp` at `/api/institutions` for public routes and `admin_inst_bp` at `/api/admin/institutions` for admin routes — both registered in `__init__.py` via a deferred import that avoids circular imports. The `_require_admin` logic duplicated into both blueprints queries `AdminSession` directly, with no import from `app/admin.py`.

The seed covers 207 entries spanning all required categories, but falls short of the stated 36 public universities (32 found) and 33 national polytechnics (25 found). The TTI and TVC sections appear county-generated rather than drawn from the TVET registry, so many are plausible but unverifiable entries rather than confirmed records.

The frontend directory view, community view, `selectMyInstitution()`, and `renderMyInstitutionBadge()` are all implemented. The "My Institution" quick-access button is present in the feed. Institution posts are fetched from `/api/institutions/:id/posts` and are entirely separate from the main `/api/feed`, meeting the isolation requirement.

The global `navigate()` function in `app.js` includes `institutions` in the FAB labels map but routes its click through `openPostForm('institutions')`, which has no branch for that value and silently falls through. The FAB is correctly overridden inside `openInstitutionCommunity()` once a user enters a specific institution's community, so the bug only affects the directory landing screen.

`member_count` on `InstitutionCommunity` is never incremented anywhere — institution selection stores the choice in `localStorage` only, there is no server-side membership call. `post_count` is correctly incremented on post creation. The "popular institutions" endpoint sorts by `member_count`, so it will always return institutions in arbitrary (insertion) order.

The admin edit form calls `openModal()`, which is defined locally in `admin.js` and works correctly in that context. The edit form pre-populates from `window._instAdminData`, which is set during tab load — a stale-data risk if the tab auto-refreshes while a modal is open, but not a blocking issue.

---

<details>
<summary>Issues (6)</summary>

1. **FAB dead code on directory landing** — `navigate('institutions')` sets `fab.onclick = () => openPostForm('institutions')`, but `openPostForm` has no `institutions` branch and does nothing. Either add the branch or exclude `institutions` from the FAB map on the directory view (the FAB is correctly handled inside `openInstitutionCommunity` once inside a community).

2. **member_count never incremented** — Institution selection only writes to `localStorage`; no API call records membership server-side. `InstitutionCommunity.member_count` stays zero for every institution, breaking the "popular institutions" sort and all displayed member counts. Either add a lightweight `POST /api/institutions/:id/join` endpoint and call it on selection, or document that member count is intentional future work and default-sort popular institutions by `post_count` instead.

3. **Seed public university count short of spec** — The task requires 36 public universities; the seed contains 32. Missing: Kisii University is present, but several recently chartered universities (e.g. Alupe is listed, Tharaka listed) need verification. Run a count against the CUE chartered list and add the missing entries before shipping.

4. **Seed national polytechnic count short of spec** — The task requires 33 national polytechnics; the seed contains 25 entries in that category. The remaining 8 should be sourced from the TVET State Department registry.

5. **Duplicate name in seed** — "Mombasa Technical Training Institute" appears twice (once as `National Polytechnic`, once as `Technical Training Institute`, abbreviations `MTTI` and `MoTTI`). The seed dedup check is case-insensitive on name, so the second entry will be silently skipped. Decide which category is correct and remove the duplicate.

6. **Reused abbreviations in seed** — `KIBU`, `RU`, `MKU`, `GU`, and `NIST` each appear on two distinct institutions. `InstitutionCategory.abbreviation` has no unique constraint, so both records are inserted, but abbreviation search in the directory will return both and the UI cannot distinguish them. Either make abbreviations unique at the DB level or assign distinct abbreviations (e.g. `RU` → `Riara` / `Rongo`).

</details>

---

<details>
<summary>Details</summary>

### FAB wiring on the directory landing page

`navigate('institutions')` in `app.js` sets the FAB label to `'✏️ Post'` and wires `onclick` to `openPostForm('institutions')`. The `openPostForm` function only handles `community`, `marketplace`, and `lostandfound`; the `institutions` branch is absent. Clicking the FAB on the directory grid does nothing. This is confirmed by reading both `app.js` lines 86–98 and `openPostForm` at line 100.

The FAB is correctly re-wired to `openInstPostForm(id)` inside `openInstitutionCommunity()` in `institutions.js`, so posting works once a user has drilled into a specific community. The bug is scoped to the directory landing view.

### member_count is permanently zero

`InstitutionCommunity.member_count` defaults to `0` and is never updated. `selectMyInstitution()` writes `{id, name, abbreviation}` to `localStorage` and calls `renderMyInstitutionBadge()` — no fetch to any server endpoint. The popular institutions endpoint (`GET /api/institutions/popular`) orders by `member_count DESC`, so the result is effectively ordered by insertion order (all counts are 0, tie-break is DB default). Every institution card in the directory also shows "0 members".

### Seed data coverage gaps

The seed reaches 207 entries but falls short on two categories the spec treats as minimums. The public university count is 32 against a required 36 (confirmed by counting `"category": "Public University"` occurrences). The national polytechnic count is 25 against a required 33. The TTI and TVC sections are exhaustive by county (one per county) rather than sourced from TVETA's accredited institution list, so they represent an approximation, not an import of the actual registry.

Five abbreviations (`KIBU`, `RU`, `MKU`, `GU`, `NIST`) are reused across distinct institutions. The name-based dedup in `seed_institutions()` will insert both entries but leave the abbreviation collision in place. `NIST` is particularly confusing: it refers to both "Nairobi International School of Theology" (Specialised, Private) and "Nyandarua Institute of Science and Technology" (National Polytechnic, Public).



</details>

---

<details>
<summary>File map</summary>

| File | What changed |
|------|-------------|
| `app/models.py` | Added `InstitutionCategory`, `Institution`, `InstitutionCommunity`, `InstitutionPost`, `InstitutionPostComment` models |
| `app/institutions.py` | New file — public API blueprint (`/api/institutions`) and admin blueprint (`/api/admin/institutions`) |
| `app/institutions_seed.py` | New file — 207-entry seed list and `seed_institutions()` function |
| `app/__init__.py` | Registered `institutions_bp` and `admin_inst_bp` via deferred import |
| `seed.py` | Added `seed_institutions()` call after `db.create_all()` |
| `static/js/institutions.js` | New file — directory view, community view, post/comment UI, `selectMyInstitution`, `renderMyInstitutionBadge` |
| `static/js/app.js` | Added `institutions: renderInstitutions` to renders map; added `institutions` to FAB labels (broken handler) |
| `static/js/feed.js` | Added My Institution quick-access button above feed |
| `static/js/admin.js` | Added `loadInstitutionsAdminTab`, `adminCreateInstitution`, `adminEditInstitutionForm`, `adminUpdateInstitution`, `adminDeactivateInstitution`, `adminImportInstitutionCSV`, local `openModal` |
| `templates/index.html` | Added Institutions nav button; added `institutions.js` script tag |
| `templates/admin.html` | Added Institutions tab button |
| `static/css/style.css` | Added institution card, badge, category tab, and community styles |

Full diff: `git -C c:\Users\user\Documents\NetBeansProjects\CampusConnect\.worktrees\institution-directory diff master...HEAD`

</details>
