-- Semana Saludable · esquema Supabase
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query → pegar y Run

create table if not exists menus_guardados (
  id uuid primary key default gen_random_uuid(),
  titulo text not null,
  dias int not null check (dias between 1 and 7),
  base jsonb not null default '[]',
  menu jsonb not null default '[]',
  compras jsonb not null default '[]',
  created_at timestamptz not null default now()
);

alter table menus_guardados enable row level security;

-- Política simple para MVP (app sin login): permitir todo al rol anon.
-- Cuando agregues Auth, reemplaza por policies por usuario (auth.uid()).
drop policy if exists "public all" on menus_guardados;
create policy "public all" on menus_guardados
  for all using (true) with check (true);
