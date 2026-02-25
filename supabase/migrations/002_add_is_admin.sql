-- Add is_admin flag to profiles for bot /stats access
alter table public.profiles
  add column if not exists is_admin boolean not null default false;
