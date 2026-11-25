-- Run only after the application schema has been applied with `flask db upgrade`.
-- Browser/mobile clients use the Supabase anon key; privileged writes stay on
-- the Flask server and use server-side credentials only.

alter table public.post enable row level security;
alter table public.comment enable row level security;
alter table public.marketplace_item enable row level security;
alter table public.lost_found_item enable row level security;
alter table public.announcement enable row level security;
alter table public.ad enable row level security;
alter table public.institution_categories enable row level security;
alter table public.institutions enable row level security;
alter table public.institution_communities enable row level security;
alter table public.institution_posts enable row level security;
alter table public.institution_post_comments enable row level security;
alter table public.ad_placements enable row level security;
alter table public.advertisements enable row level security;
alter table public.events enable row level security;
alter table public.opportunities enable row level security;
alter table public.account enable row level security;
alter table public.account_session enable row level security;
alter table public.admin_session enable row level security;
alter table public.report enable row level security;
alter table public.advertisers enable row level security;
alter table public.advertiser_sessions enable row level security;
alter table public.ad_campaigns enable row level security;
alter table public.ad_impressions enable row level security;
alter table public.ad_clicks enable row level security;
alter table public.ad_daily_stats enable row level security;
alter table public.ad_payments enable row level security;
alter table public.reactions enable row level security;
alter table public.notifications enable row level security;

drop policy if exists public_read_posts on public.post;
create policy public_read_posts on public.post for select to anon, authenticated
    using (deleted is false);
drop policy if exists public_read_comments on public.comment;
create policy public_read_comments on public.comment for select to anon, authenticated
    using (exists (
        select 1 from public.post p where p.id = comment.post_id and p.deleted is false
    ));
drop policy if exists public_read_marketplace on public.marketplace_item;
create policy public_read_marketplace on public.marketplace_item for select to anon, authenticated
    using (deleted is false and sold is false);
drop policy if exists public_read_lost_found on public.lost_found_item;
create policy public_read_lost_found on public.lost_found_item for select to anon, authenticated
    using (deleted is false and resolved is false);
drop policy if exists public_read_announcements on public.announcement;
create policy public_read_announcements on public.announcement for select to anon, authenticated
    using (true);
drop policy if exists public_read_ads on public.ad;
create policy public_read_ads on public.ad for select to anon, authenticated
    using (active is true);
drop policy if exists public_read_institution_categories on public.institution_categories;
create policy public_read_institution_categories on public.institution_categories for select to anon, authenticated
    using (true);
drop policy if exists public_read_institutions on public.institutions;
create policy public_read_institutions on public.institutions for select to anon, authenticated
    using (active is true);
drop policy if exists public_read_institution_communities on public.institution_communities;
create policy public_read_institution_communities on public.institution_communities for select to anon, authenticated
    using (exists (
        select 1 from public.institutions i
        where i.id = institution_communities.institution_id and i.active is true
    ));
drop policy if exists public_read_institution_posts on public.institution_posts;
create policy public_read_institution_posts on public.institution_posts for select to anon, authenticated
    using (deleted is false and exists (
        select 1 from public.institutions i
        where i.id = institution_posts.institution_id and i.active is true
    ));
drop policy if exists public_read_institution_post_comments on public.institution_post_comments;
create policy public_read_institution_post_comments on public.institution_post_comments for select to anon, authenticated
    using (exists (
        select 1 from public.institution_posts p
        where p.id = institution_post_comments.post_id and p.deleted is false
    ));
drop policy if exists public_read_ad_placements on public.ad_placements;
create policy public_read_ad_placements on public.ad_placements for select to anon, authenticated
    using (active is true);
drop policy if exists public_read_active_advertisements on public.advertisements;
create policy public_read_active_advertisements on public.advertisements for select to anon, authenticated
    using (status = 'active');
drop policy if exists public_read_events on public.events;
create policy public_read_events on public.events for select to anon, authenticated
    using (active is true);
drop policy if exists public_read_opportunities on public.opportunities;
create policy public_read_opportunities on public.opportunities for select to anon, authenticated
    using (active is true and (closes_at is null or closes_at >= now()));

-- The existing application uses its own account/session model. Sensitive
-- accounts, admin sessions, reports, payments and analytics have no browser
-- client policies and are therefore denied to anon/authenticated roles.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
    ('profile-pictures', 'profile-pictures', false, 5242880,
     array['image/jpeg', 'image/png', 'image/webp']),
    ('post-images', 'post-images', true, 5242880,
     array['image/jpeg', 'image/png', 'image/webp', 'image/gif']),
    ('event-posters', 'event-posters', true, 5242880,
     array['image/jpeg', 'image/png', 'image/webp']),
    ('documents', 'documents', false, 10485760,
     array['application/pdf', 'application/msword',
           'application/vnd.openxmlformats-officedocument.wordprocessingml.document']),
    ('advertisements', 'advertisements', true, 5242880,
     array['image/jpeg', 'image/png', 'image/webp']),
    ('institution-logos', 'institution-logos', true, 5242880,
     array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

drop policy if exists public_read_content_images on storage.objects;
create policy public_read_content_images on storage.objects for select to anon, authenticated
    using (bucket_id in ('post-images', 'event-posters', 'advertisements', 'institution-logos'));
