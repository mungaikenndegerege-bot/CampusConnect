# Fix Review — CampusConnect Institution Directory

Commit: `1e5248a6c02709da55a267b559a3db4356f46b4c`

## Evidence summary

### Fix 1 — FAB hidden on directory landing, shown as '✏️ Post Here' in community view

`renderInstitutions()` (institutions.js line 62–63) now retrieves `fab-btn` by ID and sets `style.display = 'none'` immediately after the county dropdown is populated, before `loadInstitutionCards` runs. This correctly hides the FAB for the whole directory view.

`openInstitutionCommunity()` (institutions.js line 258–262) sets `fab.textContent` and `fab.style.display = 'flex'`. The raw file bytes at that position are `U+270F U+FE0F` (pencil + variation-selector-16) followed by ` Post Here`, which is the full `✏️ Post Here` sequence. The terminal rendered it without the VS-16 but the byte evidence confirms the emoji is correct.

**Result: PASS**

### Fix 2 — POST /api/institutions/<id>/join endpoint

`join_institution()` added at institutions.py line 163–174. It calls `get_or_404`, creates a community record if none exists (matching the same guard pattern already used in `create_inst_post`), increments `member_count`, commits, and returns the new count. No auth required, consistent with the open-access requirement.

`selectMyInstitution()` (institutions.js line 474) calls `fetch('/api/institutions/${inst.id}/join', { method: 'POST' }).catch(() => {})` — fire-and-forget as required, before `renderMyInstitutionBadge()` and `showToast`.

**Result: PASS**

### Fix 3 — Missing public universities

Three entries added in the Public University section:
- `Masinde Muliro University of Science and Technology` / `MMUST` / Kakamega
- `Tom Mboya University` / `TMU` / Homa Bay
- `Kaimosi Friends University` / `KAFU` / Vihiga

No duplicate name matches found in the full file. Total institution count: 231, matching the commit message claim.

**Result: PASS**

### Fix 4 — Missing national polytechnics (21 entries)

The following 21 National Polytechnic entries were added in the diff and are present in the file:
Nkabune, Nyeri, Embu, Machakos, Kaiboi, Mawego, Siaya, Nyamira, Migori, Homa Bay, Voi, Kilifi, Lamu, Tana River, Garissa, Wajir, Mandera, Marsabit, Isiolo, Samburu, Laikipia — all with distinct `*NP`-pattern abbreviations. No name collisions found.

**Result: PASS**

### Fix 5 — Duplicate Mombasa Technical Training Institute removed

The diff removes the second `{"name": "Mombasa Technical Training Institute", "abbreviation": "MoTTI", ...}` entry from the TTI section (line 150 in the old file). The surviving entry at seed line 85 carries abbreviation `MTTI` in the National Polytechnic section. `Select-String` confirms exactly one occurrence of `"Mombasa Technical Training Institute"` in the file.

**Result: PASS**

### Fix 6 — Duplicate abbreviations resolved

All five collision pairs resolved with location suffixes:
| Old abbr | Institution | New abbr |
|---|---|---|
| MKU | Machakos University | MKU-Machakos |
| MKU | Mount Kenya University | MKU-Thika |
| RU | Rongo University | RU-Migori |
| RU | Riara University | RU-Nairobi |
| GU | Garissa University | GU-Garissa |
| GU | Gretsa University | GU-Thika |
| NIST | Nairobi International School of Theology | NIST-Nairobi |
| NIST | Nyandarua Institute of Science and Technology | NIST-Nyandarua |
| KIBU | Kibabii University | KIBU (unchanged — the original) |
| KIBU | Kibabii University College | KIBU-UC |

Automated abbreviation duplicate scan (via byte scan of the file) found no remaining collisions.

**Result: PASS**

## Verdict

No blockers identified. All six fix requirements are satisfied by the diff.
