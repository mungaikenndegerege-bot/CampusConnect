# CampusConnect — Requirements Document

**App name:** CampusConnect  
**Tagline:** Kila Kitu Made Easy  
**Version:** 1.0  
**Date:** 2026-11-11  

---

## Summary

CampusConnect is a mobile-first Progressive Web App (PWA) that serves as a single academic hub for university students, lecturers, and administrators across multiple independent institutions. Any number of institutions can be onboarded; each institution's data is fully isolated. The backend is Python (Flask) with SQLite via SQLAlchemy. The frontend is a vanilla JS single-page application (SPA) served from Flask's `static/` folder. The app is deployed on Render using Docker.

The platform targets ten core feature areas: authentication & role management, student dashboard, smart timetable, digital library, announcements, assignment tracker, student community, campus marketplace, lost & found, and admin panels (super-admin and institution-admin).

---

## Assumptions

> These inferences were made where the original request left gaps. The design review should confirm or correct them.

1. **PWA, not native mobile.** The user asked for a "mobile application" but also specified vanilla JS + HTML/CSS and Render deployment. A PWA (installable via browser, offline-capable manifest) is the intended delivery vehicle — no React Native or Flutter.
2. **Single HTML shell / SPA.** All page transitions happen client-side via JS; Flask serves one `index.html` and a JSON API.
3. **File uploads stored on the server filesystem** inside `static/uploads/`. On Render's free tier the filesystem is ephemeral; a production upgrade to object storage (e.g., Cloudflare R2) is out of scope for v1 but noted.
4. **JWT stored in `localStorage`.** `HttpOnly` cookies are the more secure alternative but complicate the pure-JS SPA flow. This is flagged as a known trade-off.
5. **Student "marks assignment as done"** is a client-side completion flag per student — lecturers do not grade submissions; they only see who has marked completion.
6. **Community post likes** are a simple increment counter; no per-user de-duplication is enforced in v1 (can be added later).
7. **Marketplace and Lost & Found are institution-scoped** (students in Institution A cannot see Institution B's listings), consistent with the general isolation requirement.
8. **Super admin credentials** are seeded at first run via an environment variable or a seed script, not via a registration form.
9. **No email/SMS notifications** in v1 — all communication is in-app.
10. **No real-time features** (websockets, server-sent events) in v1 — pages poll or reload.
11. **Course enrolment** is not explicitly modelled; students see all courses belonging to their institution. A future enrolment model is out of scope.
12. **Password reset** is out of scope for v1.

---

## Functional Requirements

### FR-1 Authentication & Role Management

**FR-1.1** The system shall support four roles: `super_admin`, `institution_admin`, `lecturer`, `student`.  
**FR-1.2** Users shall register with name, email, password, and institution (not applicable to `super_admin`).  
**FR-1.3** The system shall authenticate users with email + password and return a signed JWT (access token).  
**FR-1.4** Every protected API endpoint shall require a valid JWT in the `Authorization: Bearer <token>` header.  
**FR-1.5** Each user (except `super_admin`) shall belong to exactly one institution; they shall only be able to read and write data belonging to that institution.  
**FR-1.6** Role-based access control (RBAC) shall be enforced server-side on every route; the frontend shall also hide UI elements irrelevant to the current role.  
**FR-1.7** A `super_admin` account shall be created via a seed mechanism at application startup if none exists.  
**FR-1.8** Institution admins shall be able to deactivate (soft-delete) student or lecturer accounts within their institution.  
**FR-1.9** Deactivated users shall be denied login.

### FR-2 Student Dashboard

**FR-2.1** The dashboard shall display today's timetable slots (filtered to the current day of the week).  
**FR-2.2** The dashboard shall display the next five upcoming assignment deadlines (due_date ≥ today, ordered ascending).  
**FR-2.3** The dashboard shall display the three most recent announcements for the student's institution.  
**FR-2.4** The dashboard shall provide quick-link navigation buttons to Timetable, Library, Community, Marketplace, and Lost & Found.  
**FR-2.5** The dashboard data shall be served from a single `/api/dashboard` endpoint that aggregates all four data points.

### FR-3 Smart Timetable

**FR-3.1** The timetable shall display a weekly view (Mon–Sun) of all slots for the institution.  
**FR-3.2** Each slot shall show course name, room, start time, and end time.  
**FR-3.3** Slots shall be colour-coded; each course shall have a consistent hex colour stored in `TimetableSlot.color`.  
**FR-3.4** Lecturers and institution admins shall be able to create, edit, and delete timetable slots.  
**FR-3.5** Students shall have read-only access to the timetable.  
**FR-3.6** Slot fields: course (required), day of week (Mon–Sun, required), start time, end time, room (optional).

### FR-4 Digital Library

**FR-4.1** Only lecturers shall be able to upload files.  
**FR-4.2** Accepted file types: PDF, DOC, DOCX. Maximum file size: 20 MB per file.  
**FR-4.3** Each file shall be associated with a course and a category: `Notes`, `Past Papers`, `Learning Materials`, `Course Documents`.  
**FR-4.4** Students shall be able to browse files filtered by course and/or category.  
**FR-4.5** Students shall be able to download files.  
**FR-4.6** Lecturers shall be able to delete files they uploaded; institution admins shall be able to delete any file within their institution.  
**FR-4.7** File metadata (title, description, uploader name, upload date) shall be displayed in the file listing.

### FR-5 Announcements

**FR-5.1** Institution admins and lecturers shall be able to create announcements with a title and body.  
**FR-5.2** An announcement shall be visible to all users within the same institution.  
**FR-5.3** Institution admins shall be able to pin or unpin any announcement; lecturers shall be able to pin or unpin their own.  
**FR-5.4** Pinned announcements shall appear at the top of the list, ordered by `created_at` descending among pinned; unpinned follow in the same order.  
**FR-5.5** Institution admins shall be able to delete any announcement; lecturers shall be able to delete their own.

### FR-6 Assignment Tracker

**FR-6.1** Lecturers shall be able to create assignments with: title (required), description (optional), due date (required), and course (required).  
**FR-6.2** All students in the institution shall see all assignments.  
**FR-6.3** Each student shall be able to mark an assignment as "done" on their own view; this creates an `AssignmentCompletion` record.  
**FR-6.4** An assignment whose `due_date` has passed and that is not marked done by the viewing student shall be highlighted as overdue (red).  
**FR-6.5** Lecturers and institution admins shall be able to edit or delete assignments.  
**FR-6.6** The assignment list shall be sortable by due date and filterable by course.

### FR-7 Student Community

**FR-7.1** Any user within an institution (all roles) shall be able to create a post with: title (required), body (required), and topic tag: `General`, `Academic`, `Study Groups`, `Q&A`.  
**FR-7.2** Any user within the same institution shall be able to comment on a post.  
**FR-7.3** Comments shall support one level of nesting (replies to comments).  
**FR-7.4** Any user shall be able to like a post (increments a counter).  
**FR-7.5** Posts shall be filterable by topic tag.  
**FR-7.6** Posts shall be listed most-recent-first by default.  
**FR-7.7** The post author or an institution admin shall be able to delete a post (deletes associated comments).  
**FR-7.8** The comment author or an institution admin shall be able to delete a comment.

### FR-8 Campus Marketplace

**FR-8.1** Any authenticated user within an institution shall be able to list an item with: title (required), description (optional), price (required, numeric), category (`Books`, `Electronics`, `Accessories`, `Accommodation`, `Other`), and contact info (required).  
**FR-8.2** Listings shall go live immediately upon submission — no admin approval required.  
**FR-8.3** All authenticated users within the same institution shall be able to browse listings.  
**FR-8.4** The seller shall be able to mark their listing as "sold"; institution admins shall also be able to mark any listing as sold.  
**FR-8.5** Listings shall be filterable by category and by sold/available status.  
**FR-8.6** The seller or an institution admin shall be able to delete a listing.

### FR-9 Lost & Found

**FR-9.1** Any authenticated user within an institution shall be able to post a lost or found item with: type (`lost` / `found`, required), title (required), description (optional), location (optional), date occurred (required), and contact info (required).  
**FR-9.2** All authenticated users within the same institution shall be able to browse posts.  
**FR-9.3** The poster or an institution admin shall be able to mark a post as "resolved".  
**FR-9.4** Posts shall be filterable by type (`lost` / `found`) and by resolved status.  
**FR-9.5** The poster or an institution admin shall be able to delete a post.

### FR-10 Super Admin Panel

**FR-10.1** The super admin shall be able to add a new institution (name, code, optional logo URL).  
**FR-10.2** The super admin shall be able to edit institution details.  
**FR-10.3** The super admin shall be able to deactivate or reactivate an institution; deactivating an institution shall deny login to all its users.  
**FR-10.4** The super admin shall be able to view a list of all users across all institutions, with their role and institution.  
**FR-10.5** The super admin shall be able to view platform-wide statistics: total institutions, total users by role, total library files, total community posts.

### FR-11 Institution Admin Panel

**FR-11.1** The institution admin shall be able to add student accounts (name, email, temporary password).  
**FR-11.2** The institution admin shall be able to add lecturer accounts (name, email, temporary password).  
**FR-11.3** The institution admin shall be able to view all users within their institution, filtered by role.  
**FR-11.4** The institution admin shall be able to deactivate or reactivate any user within their institution.  
**FR-11.5** The institution admin shall be able to create, edit, and delete courses (name, code, assigned lecturer).  
**FR-11.6** The institution admin shall be able to post and manage announcements (covered by FR-5).

### FR-12 PWA & Frontend Shell

**FR-12.1** The app shall ship a valid `manifest.json` with app name, icons, `start_url`, `display: standalone`, and the primary brand colour.  
**FR-12.2** A service worker (`sw.js`) shall cache the app shell (HTML, CSS, core JS) for offline availability; API calls shall fail gracefully when offline.  
**FR-12.3** The frontend shall render as a single-page application from one `index.html`; routing shall be handled client-side.  
**FR-12.4** On mobile viewports (≤ 768 px) a bottom navigation bar shall be present with icons and labels for: Dashboard, Timetable, Library, Community, More.  
**FR-12.5** On desktop viewports (> 768 px) a side or top navigation shall replace the bottom bar.  
**FR-12.6** The colour scheme shall use `#6C3CE1` (deep purple) as the primary colour, white as the background, and `#F5A623` (gold) as the accent.

---

## Non-Functional Requirements

**NFR-1 Performance.** API responses for list endpoints shall return within 500 ms under normal load (single-instance SQLite). Pagination (default 20 items per page) shall be applied to all list endpoints that may return unbounded rows.

**NFR-2 Security.**  
- Passwords shall be hashed with Werkzeug's `generate_password_hash` (PBKDF2-SHA256).  
- JWTs shall expire after 24 hours; the secret key shall be loaded from an environment variable (`SECRET_KEY`), never hard-coded.  
- File uploads shall be validated for MIME type and extension server-side before saving.  
- Institution isolation shall be enforced server-side; frontend-only isolation is insufficient.

**NFR-3 Portability.**  
- The app shall run with `python run.py` locally.  
- A `Dockerfile` using `python:3.11-slim` shall allow container builds.  
- A `render.yaml` shall declare the web service for one-click Render deployment.

**NFR-4 Maintainability.**  
- Each feature domain shall live in its own Flask Blueprint module.  
- SQLAlchemy models shall all be defined in `app/models.py`.  
- Configuration (database URI, secret key, upload folder) shall be centralised in `config.py` and loaded via environment variables with safe defaults for local development.

**NFR-5 Usability.**  
- All forms shall provide inline validation feedback before submission.  
- Loading states shall be shown while API calls are in flight.  
- Error responses from the API shall include a human-readable `message` field displayed to the user.

---

## Acceptance Criteria

**AC-1** Running `python run.py` starts the Flask development server without errors, and `GET /` returns the `index.html` shell.

**AC-2** `POST /api/auth/register` with valid student data for an existing institution returns HTTP 201 and a JWT access token.

**AC-3** `POST /api/auth/login` with correct credentials returns HTTP 200 and a JWT; the same endpoint returns HTTP 401 for wrong credentials.

**AC-4** A request to any protected endpoint without a JWT returns HTTP 401; a request with a valid JWT but insufficient role returns HTTP 403.

**AC-5** A student JWT cannot read or write data belonging to a different institution — the server returns HTTP 403 or an empty list as appropriate.

**AC-6** `GET /api/dashboard` for an authenticated student returns a JSON object containing keys `today_classes`, `upcoming_assignments`, `announcements`.

**AC-7** `GET /api/timetable` for an authenticated institution user returns all timetable slots for that institution, structured by day of week.

**AC-8** A lecturer can upload a PDF via `POST /api/library/upload`; the file is saved to `static/uploads/` and its metadata is retrievable via `GET /api/library`.

**AC-9** A student calling `POST /api/library/upload` receives HTTP 403.

**AC-10** `POST /api/announcements` by an institution admin creates an announcement visible in `GET /api/announcements` for all users of that institution.

**AC-11** Pinned announcements appear before unpinned ones in `GET /api/announcements`.

**AC-12** `POST /api/assignments` by a lecturer creates an assignment; a student in the same institution can retrieve it via `GET /api/assignments`.

**AC-13** A student calling `POST /api/assignments/<id>/complete` creates an `AssignmentCompletion` record; calling it again returns HTTP 409 (already completed).

**AC-14** An overdue assignment (due_date < today, not completed) is flagged `"overdue": true` in the API response.

**AC-15** `POST /api/community/posts` creates a community post; `POST /api/community/posts/<id>/comments` adds a comment to it; both are retrievable.

**AC-16** `POST /api/marketplace/items` creates a listing immediately without admin approval; it appears in `GET /api/marketplace/items`.

**AC-17** The seller can call `PATCH /api/marketplace/items/<id>` to set `sold: true`; the item then shows as sold.

**AC-18** `POST /api/lostandfound` creates a lost/found post; calling `PATCH /api/lostandfound/<id>` with `resolved: true` marks it resolved.

**AC-19** The super admin can call `POST /api/admin/institutions` to create a new institution, and it appears in `GET /api/admin/institutions`.

**AC-20** The super admin can call `PATCH /api/admin/institutions/<id>` with `active: false` to deactivate an institution; users of that institution subsequently receive HTTP 403 on login.

**AC-21** An institution admin can call `POST /api/admin/users` to add a student; that student can then log in.

**AC-22** The `index.html` shell loads in a mobile browser, the bottom navigation bar is visible, and tapping each tab renders the corresponding section without a full page reload.

**AC-23** `manifest.json` is present at `/manifest.json` and contains `name`, `short_name`, `start_url`, `display`, `theme_color`, and at least one icon entry.

**AC-24** `sw.js` is present at `/sw.js` and registers without errors in Chrome DevTools > Application > Service Workers.

**AC-25** `docker build -t campusconnect .` completes without errors and `docker run -p 5000:5000 campusconnect` serves the application.

---

## Out of Scope (v1)

- Native iOS / Android apps (React Native, Flutter, Capacitor).
- Real-time notifications (WebSockets, push notifications, email/SMS).
- Password reset / forgot password flow.
- Student course enrolment model (students see all institution courses in v1).
- File storage on external object storage (S3, Cloudflare R2) — local filesystem only.
- Per-user like de-duplication on community posts.
- Assignment submission uploads (students mark done only; no file submission).
- Grading / marks / GPA tracking.
- Video or audio file uploads in the library.
- Payment processing in the marketplace.
- In-app messaging / direct messages between users.
- OAuth / social login (Google, Facebook).
- Multi-language / i18n support beyond the Swahili tagline.
- Automated testing suite (unit / integration tests).
- CI/CD pipeline beyond the `render.yaml` deployment config.
