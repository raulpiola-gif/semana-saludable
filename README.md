# 🥗 Semana Saludable

App que genera **recetas saludables para 1–7 días** a partir de tus ingredientes (escritos o **dictados por voz**), busca **inspiración real en internet** (TheMealDB + Google/YouTube), arma la **lista de compras** y permite **guardar menús en Supabase** + asignarlos a días del planner (pudiendo cambiarlos).

**Stack:** Python `FastAPI` (backend + auth propia) · HTML + Tailwind (frontend) · `Redis Cloud` (DB) · `Vercel` (deploy) · `GitHub` (código).

## Estructura
```
semana-saludable/
├── public/index.html       # Frontend (todo el UX, servido por el CDN)
├── api/index.py          # Backend FastAPI (POST /api/generate, GET /api/search)
├── requirements.txt
├── vercel.json
├── supabase_schema.sql   # Tabla menus_guardados
├── .env.example
```

## 1) Correr en local
```bash
cd semana-saludable
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
# abrir index.html con Live Server, o:
python3 -m http.server 5500 --directory public
# → http://localhost:5500 (la app llama a http://localhost:8000/api/...)
```

Probar API:
```bash
curl -X POST http://localhost:8000/api/generate \
 -H 'Content-Type: application/json' \
 -d '{"ingredientes":["pollo","arroz","brocoli"],"dias":3,"preferencias":[]}'
```

## 2) Redis Cloud (base + cuentas, 5 min)
1. Crea cuenta en https://redis.io/cloud → **Create Database** (plan Free) → nombre `semana-saludable`.
2. En la ficha de la DB copia el **Public endpoint** y la contraseña. La URL queda: `redis://default:PASS@HOST:PORT`.
3. En Vercel: tu proyecto → **Settings → Environment Variables** → agrega `REDIS_URL` y `APP_SECRET` (cadena larga aleatoria) → **Redeploy**.
4. En local: `export REDIS_URL=... APP_SECRET=...` + `pip install -r requirements.txt`.
> Sin `REDIS_URL` la app funciona igual, pero los menús se guardan solo en el navegador.

## 3) Login
Botón **Ingresar → Crear cuenta** (email + contraseña, sin confirmación por correo). Cada usuario ve solo sus menús. El planner sigue local por dispositivo.

## Migración desde Supabase (una sola vez, opcional)
1. Crea tu cuenta en la app.
2. `pip install redis && python3 scripts/migrate_supabase_to_redis.py --owner-email TU@EMAIL --supabase-url ... --supabase-key ... --redis-url ...`

## 4) GitHub
```bash
cd semana-saludable
git init
git add .
git commit -m "feat: app semana saludable (fastapi + supabase + vercel)"
gh repo create semana-saludable --public --source=. --remote=origin --push
# o si ya existe el repo:
# git remote add origin https://github.com/TU-USUARIO/semana-saludable.git
# git branch -M main && git push -u origin main
```

## 5) Publicar en Vercel
```bash
npm i -g vercel
vercel          # acepta defaults (root = semana-saludable/)
vercel --prod
```
- Frontend: `public/index.html` (CDN estático). Backend: `api/index.py` (función Python).
- No requiere variables de entorno (Supabase se configura desde el botón ⚙️ en el navegador).

## 6) Modo IA (opcional, recetas generativas)
Sin clave, el tab IA usa el circuito normal con fallback. Para activar recetas 100% generadas:
1. Crea una clave **gratis** en https://console.groq.com/keys.
2. En Vercel: tu proyecto → **Settings → Environment Variables** → agrega:
   - `OPENAI_API_KEY` = tu clave
   - `OPENAI_BASE_URL` = `https://api.groq.com/openai/v1`
   - `OPENAI_MODEL` = `openai/gpt-oss-120b`
3. **Redeploy** (Deployments → ⋯ → Redeploy) para que tome las variables.
4. En local: `export OPENAI_API_KEY=...` antes de `uvicorn`.
El tab IA muestra "sin clave" hasta configurarla. Sirve cualquier endpoint OpenAI-compatible.

## Funciones
- Dictado por voz continuo (Web Speech API, es-ES) + carga escrita + chips rápidos.
- Globos de días seleccionables (1–7) + preferencias (vegetariano/vegano/sin gluten/rápido/económico/proteína).
- 40+ recetas saludables clásicas (mexicana, italiana, oriental, libanesa…): tus ingredientes son la base, no el límite. Cada generación varía y el botón Otras ideas evita repetir.
- Tres orígenes: **Argentina** (default: recetas reales de Paulina Cocina, Clarín, TN, Cookpad… extraídas en vivo), **Internet** (TheMealDB mundial con traducción) y **Clásicas** (selección saludable en español). Con fallback automático.
- Vista por día: título → detalle (ingredientes a comprar, pasos, tip).
- Lista de compras agregada + copiar + exportar a WhatsApp.
- Login (email + Google) y menús guardados por usuario en Supabase (o local sin cuenta).
- Planner: asignar menú a un día y **cambiarlo**.
