# CampusConnect API

The API uses JSON for normal requests and `multipart/form-data` for image and
file uploads. Reads and updates commonly return HTTP `200`; creates commonly
return HTTP `201`, except an idempotency replay, which returns `200`.

## Authentication headers

| Header | Purpose |
|---|---|
| `X-Account-Token` | Optional student account session |
| `X-Admin-Token` | Administrator session |
| `X-Advertiser-Token` | Advertiser session |
| `Idempotency-Key` | Optional unique request key for supported create endpoints |

## Public content

| Method | Route | Description |
|---|---|---|
| GET | `/api/feed` | Combined latest feed |
| GET | `/api/posts?page=1` | Community posts |
| POST | `/api/posts` | Create a community post |
| PUT/DELETE | `/api/posts/{id}` | Edit or remove a post with its `owner_token` |
| GET | `/api/posts/{id}/comments` | List comments |
| POST | `/api/posts/{id}/comments` | Add a comment |
| GET | `/api/marketplace?page=1` | Marketplace listings |
| POST | `/api/marketplace` | Create a listing |
| PUT/DELETE | `/api/marketplace/{id}` | Edit or remove a listing with its `owner_token` |
| GET | `/api/lostandfound?page=1` | Lost-and-found records |
| POST | `/api/lostandfound` | Create a report |
| PUT/DELETE | `/api/lostandfound/{id}` | Edit or remove a report with its `owner_token` |
| GET/POST | `/api/events` | List or create campus events |
| PUT/DELETE | `/api/events/{id}` | Edit or deactivate an event with its `owner_token` |
| GET/POST | `/api/opportunities` | List or create jobs and internships |
| PUT/DELETE | `/api/opportunities/{id}` | Edit or deactivate an opportunity with its `owner_token` |
| POST | `/api/reactions` | Add or update an authenticated user's reaction |
| DELETE | `/api/reactions/{target_type}/{target_id}` | Remove the authenticated user's reaction |
| GET | `/api/notifications` | List notifications for the authenticated account |
| PUT | `/api/notifications/{id}/read` | Mark an authenticated user's notification read |
| GET | `/api/announcements` | Announcements |
| GET | `/api/ads/active` | Active advertisements |
| POST | `/api/report` | Report content |

## Accounts

| Method | Route | Description |
|---|---|---|
| POST | `/api/accounts/register` | Register an account |
| POST | `/api/accounts/login` | Log in |
| GET | `/api/accounts/me` | Get the signed-in account |
| PUT | `/api/accounts/me` | Update account profile |
| POST | `/api/accounts/logout` | End an account session |

Registration example:

```json
{
  "name": "Jane Kamau",
  "email": "jane@example.com",
  "password": "replace-with-a-strong-password"
}
```

Login example:

```json
{
  "email": "jane@example.com",
  "password": "replace-with-a-strong-password"
}
```

## Institutions

| Method | Route | Description |
|---|---|---|
| GET | `/api/institutions` | Search and list institutions |
| GET | `/api/institutions/categories` | Institution categories |
| GET | `/api/institutions/counties` | Available counties |
| GET | `/api/institutions/popular` | Popular communities |
| GET | `/api/institutions/{id}` | Institution details |
| POST | `/api/institutions/{id}/join` | Increase community membership |
| GET | `/api/institutions/{id}/posts` | Institution posts |
| POST | `/api/institutions/{id}/posts` | Create an institution post |
| GET | `/api/institutions/{id}/posts/{postId}/comments` | List comments |
| POST | `/api/institutions/{id}/posts/{postId}/comments` | Add a comment |

Institution search supports `q`, `category`, `county`, `ownership`, `page`, and
`per_page` query parameters.

Reaction and notification endpoints require a valid `X-Account-Token`.

Institution post creation (`POST /api/institutions/{id}/posts`) also supports
`Idempotency-Key` and returns an `owner_token` for later edit operations.

## Idempotent create requests and owner tokens

The browser sends an `Idempotency-Key` for community posts, marketplace and
lost-and-found listings, events, opportunities, and institution posts. API
clients may do the same. Keys must contain 16 to 200 characters. Reuse the same
key only when retrying the same logical submission. The server stores only a
hash of the key and returns the original resource and owner token for retries;
a first successful create returns HTTP `201`, and a replay returns HTTP `200`.
The key is optional for backward-compatible clients.

The create response includes an opaque `owner_token`. Supply it in the JSON
body for that resource's edit/delete endpoints. Keep it private; the browser
stores it in local storage so the original poster can manage the content.
Token-based ownership does not use or trust the displayed poster name.

Example request:

```http
POST /api/posts
Content-Type: application/json
Idempotency-Key: 8bc09d44-046f-41d9-a3dd-2d225c25009d
```

## Advertiser API

Advertiser routes use `X-Advertiser-Token`.

| Method | Route | Description |
|---|---|---|
| POST | `/api/advertiser/register` | Register |
| POST | `/api/advertiser/login` | Log in |
| GET/PUT | `/api/advertiser/me` | View or update account |
| POST | `/api/advertiser/logout` | Log out |
| GET | `/api/advertiser/placements` | Active placements |
| GET/POST | `/api/advertiser/campaigns` | Campaign list/create |
| GET | `/api/advertiser/campaigns/{id}` | Campaign details |
| GET | `/api/advertiser/campaigns/{id}/stats` | Campaign statistics |
| GET | `/api/advertiser/campaigns/{id}/report` | CSV-style reporting |

## Administrator API

Administrator routes require `X-Admin-Token`.

Use `/api/admin/login` to obtain a token, then include it in subsequent
administrator requests.

Main route groups include:

- `/api/admin/ads`
- `/api/admin/announcements`
- `/api/admin/posts`
- `/api/admin/marketplace`
- `/api/admin/lostandfound`
- `/api/admin/reports`
- `/api/admin/advertisers`
- `/api/admin/campaigns`
- `/api/admin/placements`
- `/api/admin/revenue`
- `/api/admin/payments`
- `/api/admin/accounts`
- `/api/admin/accounts/{id}/status`
- `/api/admin/stats`

## Tracking and uploads

| Method | Route | Description |
|---|---|---|
| POST | `/api/track/impression` | Record an ad impression |
| POST | `/api/track/click/{advertisementId}` | Record a click |
| GET | `/api/uploads/{filename}` | Retrieve an uploaded file |
| GET | `/health` | Health check |

## Error responses

```json
{"error": "Description of the problem"}
```

Common status codes:

- `400` Invalid or missing request data
- `401` Missing or invalid session
- `403` Authenticated but not authorized
- `404` Record not found
- `409` Duplicate account or record
- `429` Too many requests
- `503` Required service configuration missing

## Validation status

The focused Python suite covers content ownership, supported create flows,
idempotent retries, upload signature rejection, administrator fail-closed
configuration, and the health check. It does not replace live Supabase policy
validation, end-to-end browser tests, or production load testing.
