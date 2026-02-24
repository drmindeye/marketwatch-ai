-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ─────────────────────────────────────────
-- profiles
-- ─────────────────────────────────────────
create table if not exists public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text unique not null,
  full_name    text,
  phone        text,
  tier         text not null default 'free' check (tier in ('free', 'pro', 'elite')),
  telegram_id  text,
  whatsapp     text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- RLS
alter table public.profiles enable row level security;

create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name'
  );
  return new;
end;
$$;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ─────────────────────────────────────────
-- alerts
-- ─────────────────────────────────────────
create table if not exists public.alerts (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  symbol      text not null,
  alert_type  text not null check (alert_type in ('touch', 'cross', 'near')),
  price       numeric(20, 5) not null,
  direction   text check (direction in ('above', 'below')),
  pip_buffer  numeric(10, 1) default 5,
  is_active   boolean not null default true,
  triggered_at timestamptz,
  created_at  timestamptz not null default now()
);

alter table public.alerts enable row level security;

create policy "Users manage own alerts"
  on public.alerts for all
  using (auth.uid() = user_id);

-- ─────────────────────────────────────────
-- subscriptions
-- ─────────────────────────────────────────
create table if not exists public.subscriptions (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  paystack_ref    text unique not null,
  plan            text not null check (plan in ('pro', 'elite')),
  status          text not null default 'active' check (status in ('active', 'cancelled', 'expired')),
  amount          numeric(12, 2) not null,
  currency        text not null default 'NGN',
  started_at      timestamptz not null default now(),
  expires_at      timestamptz,
  created_at      timestamptz not null default now()
);

alter table public.subscriptions enable row level security;

create policy "Users view own subscriptions"
  on public.subscriptions for select
  using (auth.uid() = user_id);

-- ─────────────────────────────────────────
-- market_news
-- ─────────────────────────────────────────
create table if not exists public.market_news (
  id          uuid primary key default uuid_generate_v4(),
  title       text not null,
  summary     text,
  source      text,
  url         text,
  symbol      text,
  sentiment   text check (sentiment in ('positive', 'negative', 'neutral')),
  published_at timestamptz,
  created_at  timestamptz not null default now()
);

alter table public.market_news enable row level security;

create policy "Authenticated users can read news"
  on public.market_news for select
  to authenticated
  using (true);

-- ─────────────────────────────────────────
-- updated_at auto-trigger
-- ─────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.set_updated_at();
