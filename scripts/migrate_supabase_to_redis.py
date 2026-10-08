#!/usr/bin/env python3
"""Migra menus_guardados de Supabase a Redis Cloud (una vez).

Uso:
  pip install redis
  python3 scripts/migrate_supabase_to_redis.py --owner-email TU@EMAIL \\
      --supabase-url https://xyz.supabase.co \\
      --supabase-key sb_publishable_... \\
      --redis-url 'redis://default:PASS@HOST:PORT'

Requiere que TU@EMAIL ya tenga cuenta creada en la app (botón Ingresar).
Todas las filas legacy se asignan a ese usuario. Sin --owner-email se
importan con su user_id original (solo visibles si coincide con una cuenta).
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
import uuid

import redis


def supabase_rows(url, key):
    endpoint = f"{url.rstrip('/')}/rest/v1/menus_guardados?select=*"
    req = urllib.request.Request(
        endpoint, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", errors="ignore"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner-email", default="")
    ap.add_argument("--supabase-url", required=True)
    ap.add_argument("--supabase-key", required=True)
    ap.add_argument("--redis-url", required=True)
    a = ap.parse_args()

    rows = supabase_rows(a.supabase_url, a.supabase_key)
    print(f"Filas en Supabase: {len(rows)}")

    r = redis.from_url(a.redis_url, decode_responses=True, socket_timeout=10)
    r.ping()
    print("Redis OK")

    uid = None
    if a.owner_email:
        email = a.owner_email.strip().lower()
        uid = r.get(f"user:email:{email}")
        if not uid:
            raise SystemExit(f"No existe {email} en Redis: crea tu cuenta en la app primero.")
        print(f"Dueño: {email} -> {uid}")

    n = 0
    for row in rows:
        mid = row.get("id") or uuid.uuid4().hex
        owner = uid or row.get("user_id") or "legacy"
        r.hset(f"menu:{mid}", mapping={
            "user_id": owner,
            "titulo": row.get("titulo") or "Sin título",
            "dias": int(row.get("dias") or 7),
            "base": json.dumps(row.get("base") or []),
            "menu": json.dumps(row.get("menu") or []),
            "compras": json.dumps(row.get("compras") or []),
            "comensales": int(row.get("comensales") or 4),
            "created_at": row.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        if uid:
            try:
                ts = time.mktime(time.strptime(str(row.get("created_at") or "")[:19],
                                               "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                ts = time.time()
            r.zadd(f"menus:{uid}", {mid: ts})
        n += 1
    print(f"Migrados: {n} menús")


if __name__ == "__main__":
    main()
