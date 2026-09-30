-- Semana Saludable · esquema Supabase (v2 con login por usuario)
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query → pegar y Run
-- Es re-ejecutable: si ya tienes la tabla del MVP, solo agrega user_id y ajusta policies.

create table if not exists menus_guardados (
  id uuid primary key default gen_random_uuid(),
  titulo text not null,
  dias int not null check (dias between 1 and 7),
  base jsonb not null default '[]',
  menu jsonb not null default '[]',
  compras jsonb not null default '[]',
  created_at timestamptz not null default now()
);

-- Dueño del menú (Supabase Auth). NULL = menús del MVP sin login (legacy).
alter table menus_guardados
  add column if not exists user_id uuid references auth.users(id) on delete cascade;

create index if not exists idx_menus_user on menus_guardados(user_id);

alter table menus_guardados enable row level security;

-- Reemplaza la policy abierta del MVP por policies por usuario.
drop policy if exists "public all" on menus_guardados;
drop policy if exists "leer propios o legacy" on menus_guardados;
drop policy if exists "crear propios" on menus_guardados;
drop policy if exists "editar propios" on menus_guardados;
drop policy if exists "borrar propios" on menus_guardados;

-- Leer: tus menús + legacy (user_id NULL) para no perder lo guardado antes del login.
create policy "leer propios o legacy" on menus_guardados
  for select using (auth.uid() = user_id or user_id is null);

-- Crear: solo logueado y como dueño.
create policy "crear propios" on menus_guardados
  for insert with check (auth.uid() = user_id and user_id is not null);

-- Editar / borrar: solo el dueño.
create policy "editar propios" on menus_guardados
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "borrar propios" on menus_guardados
  for delete using (auth.uid() = user_id);
