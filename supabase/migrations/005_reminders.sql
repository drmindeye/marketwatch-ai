-- Reminders: session reminders (London/NY/Asian) + custom time reminders

create table if not exists public.reminders (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  message      text not null,
  remind_at    timestamptz not null,
  session_type text check (session_type in ('asian', 'london', 'new_york')),
  is_recurring boolean not null default false,
  sent         boolean not null default false,
  created_at   timestamptz not null default now()
);

create index if not exists reminders_remind_at_sent
  on public.reminders (remind_at, sent)
  where sent = false;

alter table public.reminders enable row level security;

create policy "Users manage own reminders"
  on public.reminders for all
  using (auth.uid() = user_id);
