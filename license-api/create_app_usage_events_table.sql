-- App usage event stream (append-only)
-- Keeps a historical record of telemetry events (tour steps, step navigation, etc.)
-- while the existing app_usage table continues to act as a "latest seen" snapshot.

create table if not exists public.app_usage_events (
  id bigserial primary key,
  device_id varchar not null,
  app_version varchar,
  action varchar not null,
  platform varchar,
  created_at timestamptz not null default now(),
  details jsonb
);

create index if not exists idx_app_usage_events_created_at on public.app_usage_events (created_at desc);
create index if not exists idx_app_usage_events_device_id on public.app_usage_events (device_id);
create index if not exists idx_app_usage_events_action on public.app_usage_events (action);
