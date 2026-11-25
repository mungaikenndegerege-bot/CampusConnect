# CampusConnect administrator guide

## Access

Open `/admin` and sign in with the `ADMIN_USERNAME` and `ADMIN_PASSWORD`
configured in the hosting environment.

The credentials must be private. Do not expose them in source code,
documentation, screenshots, browser scripts, or public issue reports.

If login returns “Admin login is not configured,” add both environment variables
and redeploy.

## Dashboard areas

### Ads

- Create and edit legacy advertisements.
- Add title, body, image, link, and active status.
- Remove advertisements that are no longer valid.

### Announcements

- Publish campus-wide announcements.
- Delete outdated announcements.
- Pin important announcements when supported.

### Posts

- Review community content.
- Hide posts that violate community standards.

### Marketplace

- Hide deceptive or inappropriate listings.
- Review reported marketplace content.

### Lost & Found

- Hide resolved or abusive reports.
- Keep active reports visible for reunification.

### Reports

- Review pending reports.
- Inspect the related content preview.
- Resolve reports after action or review.

### Accounts and platform statistics

- Review account records and basic platform counts through the administrator
  API.
- Suspend an account when needed; suspension also revokes its active account
  sessions.
- Document the reason and follow the platform's moderation policy.
- Account management is currently a basic control, not a granular role or
  audited case-management system.

### Institutions

- Search and manage institution records.
- Add, update, or deactivate institutions.
- Import institution data through a CSV workflow.

### Advertisers

- Review registration requests.
- Approve or reject advertisers.
- Only approve advertisers whose identity and purpose are verified.

### Campaigns

- Approve, reject, pause, or activate campaigns.
- Verify campaign dates and placement.
- Confirm that advertisements contain accurate links and imagery.

### Placements

- Create or update advertising placements.
- Set daily prices and descriptions.
- Deactivate placements that are unavailable.

### Revenue and payments

- Review revenue totals.
- Inspect pending payments.
- Confirm legitimate payments and maintain an external audit trail.

## Moderation policy

Recommended actions:

1. Confirm the report.
2. Check the original content and supporting evidence.
3. Remove or deactivate clear violations.
4. Resolve the report.
5. Record the reason outside the platform if a formal audit log is required.

Escalate fraud, threats, identity misuse, and legal claims rather than handling
them solely through account deletion.

## Session security

- Use a unique strong password.
- Sign out on shared devices.
- Rotate `ADMIN_PASSWORD` after suspected exposure.
- Restrict hosting environment access.
- Back up PostgreSQL before bulk moderation actions.
