# 🥗 Semana Saludable

App que genera **recetas saludables para 1–7 días** a partir de tus ingredientes (escritos o **dictados por voz**), busca **inspiración real en internet** (TheMealDB + Google/YouTube), arma la **lista de compras** y permite **guardar menús en Supabase** + asignarlos a días del planner (pudiendo cambiarlos).

**Stack:** Python `FastAPI` (backend) · HTML + Tailwind (frontend, UX moderna) · `Supabase` (DB) · `Vercel` (deploy) · `GitHub` (código).

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

## 2) Supabase (5 min)
1. Crea proyecto en https://supabase.com → copia **Project URL** y **anon key**.
2. Ve a **SQL Editor** → pega el contenido de `supabase_schema.sql` → **Run**.
3. Abre la app → botón **⚙️ Supabase** → pega URL + key → Guardar.
4. Listo: **💾 Guardar menú** escribe en la tabla `menus_guardados`.

> Sin Supabase configurado la app igual funciona (guarda en el navegador).

## 3) GitHub
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

## 4) Publicar en Vercel
```bash
npm i -g vercel
vercel          # acepta defaults (root = semana-saludable/)
vercel --prod
```
- Frontend: `public/index.html` (CDN estático). Backend: `api/index.py` (función Python).
- No requiere variables de entorno (Supabase se configura desde el botón ⚙️ en el navegador).

## Funciones
- 🎙️ Dictado por voz (Web Speech API, es-ES) + carga escrita + chips rápidos.
- 📅 Slider 1–7 días + preferencias (vegetariano/vegano/sin gluten/rápido/económico/proteína).
- 🍲 24 recetas saludables curadas: tus ingredientes son la base, no el límite.
- 🌍 Búsqueda internet real: TheMealDB (sin key) + enlaces Google/YouTube por receta.
- 📖 Vista por día: título → detalle (ingredientes a comprar, pasos, tip).
- 🛒 Lista de compras agregada + copiar.
- 💾 Guardar menús (Supabase o local), abrir, borrar.
- 📅 Planner: asignar menú a un día y **cambiarlo** (🔄 / ✏️).
