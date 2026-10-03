-- Run once in the Supabase dashboard: SQL Editor -> New query -> Run
create table if not exists public.cruises (
    id              bigint generated always as identity primary key,
    page            int  not null,
    cruise_name     text not null,
    nights          int  not null,
    departure_port  text not null,
    itinerary_note  text not null default 'No Note',
    locations       text not null,
    banner_tag      text not null default 'No Banner',
    offer           text not null default 'No Offer',
    price_from_inr  int  not null,
    num_dates       int  not null,
    link            text,
    unique (cruise_name, locations, price_from_inr, num_dates, banner_tag, page)
);

-- The web app reads with the public anon key, so allow read-only access.
alter table public.cruises enable row level security;
drop policy if exists "public read" on public.cruises;
create policy "public read" on public.cruises for select using (true);

-- Make sure the public (anon) role can read the table even if "Automatically expose new tables" was off.
grant usage on schema public to anon, authenticated;
grant select on public.cruises to anon, authenticated;
