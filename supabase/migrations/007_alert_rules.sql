-- 007: 자동 알림 규칙 (11/18). 관리자가 '알림 관리'에서 켜기/끄기 · 며칠 전부터 · 최대 노출 개수를 고친다.
-- append-only: 고치기·끄기도 새 행 (entry_id = 규칙 번호: open / end / near / del_ok / del_no / notice). 여러 번 돌려도 안전하다.

create table if not exists public.alert_rules (
  row_id      text primary key,
  entry_id    text not null,
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  rule        text not null default '' check (rule in ('', 'open', 'end', 'near', 'del_ok', 'del_no', 'notice')),
  enabled     text not null default '1' check (enabled in ('0', '1')),
  days        text not null default '' check (days = '' or days ~ '^[0-9]{1,2}$'),
  max_items   text not null default '' check (max_items = '' or max_items ~ '^[0-9]{1,2}$'),
  unique (entry_id, revision)
);
create index if not exists alert_rules_entry_idx on public.alert_rules (entry_id);

alter table public.alert_rules enable row level security;
drop policy if exists alert_rules_select on public.alert_rules;
drop policy if exists alert_rules_insert on public.alert_rules;
create policy alert_rules_select on public.alert_rules for select to anon, authenticated using (true);
create policy alert_rules_insert on public.alert_rules for insert to anon, authenticated with check (true);

grant select, insert on public.alert_rules to anon, authenticated;
revoke update, delete, truncate on public.alert_rules from anon, authenticated;
