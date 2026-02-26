-- Migration 006: Correlation zone alerts table
-- Run in Supabase Dashboard → SQL Editor

create table if not exists public.correlation_alerts (
  id           uuid primary key default uuid_generate_v4(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  symbol1      text not null,
  symbol2      text not null,
  zone_low     numeric(20, 5) not null,
  zone_high    numeric(20, 5) not null,
  is_active    boolean not null default true,
  triggered_at timestamptz,
  triggered_by text,
  created_at   timestamptz not null default now()
);

alter table public.correlation_alerts enable row level security;

create policy "Users manage own correlation alerts"
  on public.correlation_alerts for all
  using (auth.uid() = user_id);
