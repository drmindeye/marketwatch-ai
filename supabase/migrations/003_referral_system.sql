-- Referral system: each user gets a unique code; track who referred whom

alter table public.profiles
  add column if not exists referral_code text unique,
  add column if not exists referred_by   uuid references public.profiles(id),
  add column if not exists referral_count integer not null default 0;

-- Auto-generate 8-char alphanumeric referral code on profile insert
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

-- Back-fill existing profiles that have no code yet
update public.profiles
  set referral_code =
        upper(substring(replace(gen_random_uuid()::text, '-', '') for 8))
  where referral_code is null;

-- RPC used by payment webhook to safely increment referral_count
create or replace function public.increment_referral_count(referrer_id uuid)
returns void language sql security definer as $$
  update public.profiles
    set referral_count = referral_count + 1
    where id = referrer_id;
$$;
