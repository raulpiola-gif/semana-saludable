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
2. Ve a **SQL Editor** → pega el contenido de `supabase_schema.sql` → **Run** (re-ejecutable: si ya lo corriste antes, vuelve a correrlo para agregar login).
3. Abre la app → botón **⚙️ Supabase** → pega URL + key → Guardar.

## 3) Login
1. En Supabase ve a **Authentication → Sign In / Up** y verifica que **Email** esté habilitado.
2. Para entrar sin confirmar el correo: **Authentication → Settings** → desactiva **Confirm email** (solo para desarrollo personal).
3. (Opcional) Google: **Authentication → Providers → Google** → crea el Client ID en Google Cloud Console y agrega como **Redirect URL** la URL de tu app en Vercel.
4. En la app pulsa **Ingresar** (arriba a la derecha) → crea tu cuenta o entra con Google. El botón **💾 Guardar menú** ahora guarda en tu cuenta (cada usuario ve solo sus menús; el planner sigue siendo local por dispositivo).

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

## Funciones
- Dictado por voz continuo (Web Speech API, es-ES) + carga escrita + chips rápidos.
- Globos de días seleccionables (1–7) + preferencias (vegetariano/vegano/sin gluten/rápido/económico/proteína).
- 40+ recetas saludables curadas (mexicana, italiana, oriental, libanesa…): tus ingredientes son la base, no el límite. Cada generación varía y el botón Otras ideas evita repetir.
- Tres orígenes: **Argentina** (default: recetas reales de Paulina Cocina, Clarín, TN, Cookpad… extraídas en vivo), **Internet** (TheMealDB mundial con traducción) y **Curadas** (selección saludable en español). Con fallback automático.
- Vista por día: título → detalle (ingredientes a comprar, pasos, tip).
- Lista de compras agregada + copiar + exportar a WhatsApp.
- Login (email + Google) y menús guardados por usuario en Supabase (o local sin cuenta).
- Planner: asignar menú a un día y **cambiarlo**.
