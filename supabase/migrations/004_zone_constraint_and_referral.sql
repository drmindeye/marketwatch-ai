-- Migration 004: Update zone alert constraint + referral system
-- Run this in Supabase Dashboard → SQL Editor

-- ─────────────────────────────────────────
-- 1. Update alert_type check constraint to include 'zone'
--    (safe no-op if the constraint already includes zone)
-- ─────────────────────────────────────────
do $$
begin
  -- Drop old constraint that excludes 'zone'
  if exists (
    select 1 from information_schema.constraint_column_usage
    where table_name = 'alerts' and constraint_name = 'alerts_alert_type_check'
  ) then
    alter table public.alerts drop constraint alerts_alert_type_check;
  end if;
end
$$;

-- Re-add with zone included (idempotent via DO block drop above)
alter table public.alerts
  add constraint alerts_alert_type_check
  check (alert_type in ('touch', 'cross', 'near', 'zone'));

-- ─────────────────────────────────────────
-- 2. Referral system columns
-- ─────────────────────────────────────────
alter table public.profiles
  add column if not exists referral_code  text unique,
  add column if not exists referred_by    uuid references public.profiles(id),
  add column if not exists referral_count integer not null default 0;

-- ─────────────────────────────────────────
-- 3. Auto-generate referral code on profile insert
-- ─────────────────────────────────────────
create or replace function public.generate_referral_code()
returns trigger language plpgsql as $$
begin
  if new.referral_code is null then
    new.referral_code :=
      upper(substring(replace(gen_random_uuid()::text, '-', '') for 8));
  end if;
  return new;
end;
$$;

drop trigger if exists set_referral_code on public.profiles;
create trigger set_referral_code
  before insert on public.profiles
  for each row execute function public.generate_referral_code();

-- ─────────────────────────────────────────
-- 4. Back-fill existing profiles without a code
-- ─────────────────────────────────────────
update public.profiles
  set referral_code =
        upper(substring(replace(gen_random_uuid()::text, '-', '') for 8))
  where referral_code is null;

-- ─────────────────────────────────────────
-- 5. RPC for payment webhook to credit referrer
-- ─────────────────────────────────────────
create or replace function public.increment_referral_count(referrer_id uuid)
returns void language sql security definer as $$
  update public.profiles
    set referral_count = referral_count + 1
    where id = referrer_id;
$$;
