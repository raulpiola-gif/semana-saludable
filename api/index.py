"""
Semana Saludable API — FastAPI backend para Vercel + desarrollo local.
- POST /api/generate : genera menú de 1-7 días a partir de ingredientes
- GET  /api/search   : busca recetas reales en internet (TheMealDB, sin key)
- GET  /api/health   : healthcheck
Compatible con Vercel Python Runtime (exporta `app`) y con `uvicorn api.index:app`.
"""

import os
import random
import re
import unicodedata
import urllib.parse
import urllib.request
import json
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Semana Saludable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------- base de recetas
# Cada receta: ingredientes_base (para matcheo), resto de campos para UI.
RECETAS = [
    {
        "id": "bowl-quinoa-pollo",
        "titulo": "Bowl de quinoa con pollo y palta",
        "descripcion": "Bowl alto en proteína, fresco y saciante. Perfecto meal-prep.",
        "tiempo": "25 min", "calorias": "520 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "sin-gluten", "meal-prep"],
        "ingredientes_base": ["pollo", "quinoa", "palta", "aguacate", "tomate", "limon", "espinaca"],
        "ingredientes_detalle": ["200g pechuga de pollo", "1 taza quinoa cocida", "1 palta", "1 taza tomates cherry", "2 tazas espinaca", "Jugo de 1 limón", "1 cda aceite de oliva", "Sal, pimienta, comino"],
        "pasos": ["Cocinar la quinoa 15 min y dejar enfriar.", "Grillar el pollo con sal, pimienta y comino, luego cortar en tiras.", "Armar el bowl con espinaca, quinoa, tomate y palta.", "Aliñar con limón y oliva."],
        "tip": "Cocina doble quinoa y guarda para otro día.",
    },
    {
        "id": "tacos-pescado",
        "titulo": "Tacos de pescado al horno con repollo",
        "descripcion": "Crujientes sin fritura, con salsa de yogur y lima.",
        "tiempo": "30 min", "calorias": "480 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "sin-fritura"],
        "ingredientes_base": ["pescado", "merluza", "tilapia", "repollo", "zanahoria", "limon", "yogur", "tortilla"],
        "ingredientes_detalle": ["500g pescado blanco", "8 tortillas de maíz", "2 tazas repollo morado", "1 zanahoria rallada", "1 yogur natural", "1 lima", "Pimentón, ajo en polvo, sal"],
        "pasos": ["Condimentar el pescado y hornear 12-15 min a 200°C.", "Mezclar yogur con lima para la salsa.", "Armar tacos con repollo, zanahoria, pescado y salsa."],
        "tip": "Usa tortillas integrales para más fibra.",
    },
    {
        "id": "ensalada-lentejas",
        "titulo": "Ensalada tibia de lentejas y verduras",
        "descripcion": "Rica en hierro y fibra, muy económica.",
        "tiempo": "30 min", "calorias": "430 kcal", "dificultad": "Fácil",
        "tags": ["vegetariano", "vegano", "economico", "alto-hierro"],
        "ingredientes_base": ["lentejas", "zanahoria", "cebolla", "tomate", "espinaca", "limon"],
        "ingredientes_detalle": ["1 1/2 taza lentejas cocidas", "1 zanahoria en cubos", "1/2 cebolla morada", "1 taza tomates cherry", "2 puñados espinaca", "Aceite oliva, vinagre, sal"],
        "pasos": ["Saltear zanahoria y cebolla 5 min.", "Mezclar con lentejas tibias.", "Sumar tomate y espinaca, aliñar."],
        "tip": "Agrega huevo duro para más proteína.",
    },
    {
        "id": "salmon-verduras",
        "titulo": "Salmón al horno con brócoli y papa",
        "descripcion": "Omega-3 + cena en una sola bandeja.",
        "tiempo": "25 min", "calorias": "550 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "omega3", "una-bandeja"],
        "ingredientes_base": ["salmon", "brocoli", "papa", "patata", "limon", "ajo"],
        "ingredientes_detalle": ["2 filetes de salmón", "1 brócoli en floretes", "3 papas en cuñas", "2 dientes ajo", "Limón, oliva, sal, pimienta"],
        "pasos": ["Hornear papas 10 min a 200°C.", "Sumar salmón y brócoli, hornear 12 min más.", "Terminar con limón."],
        "tip": "No sobrecocines el salmón: debe estar jugoso.",
    },
    {
        "id": "pollo-curry",
        "titulo": "Curry liviano de pollo y verduras con arroz integral",
        "descripcion": "Cremoso con leche de coco light, sin crema.",
        "tiempo": "35 min", "calorias": "540 kcal", "dificultad": "Media",
        "tags": ["alto-proteina", "sin-gluten"],
        "ingredientes_base": ["pollo", "arroz", "zanahoria", "cebolla", "zapallo", "calabaza", "coco", "curry"],
        "ingredientes_detalle": ["500g pollo en cubos", "1 taza arroz integral cocido", "1 cebolla", "2 zanahorias", "2 tazas zapallo", "200ml leche de coco light", "2 cda curry en polvo"],
        "pasos": ["Dorar pollo y reservar.", "Saltear verduras con curry.", "Sumar coco y pollo, cocinar 15 min. Servir sobre arroz."],
        "tip": "Agrega espinaca al final para más verde.",
    },
    {
        "id": "omelette-verduras",
        "titulo": "Omelette de claras y verduras con ensalada",
        "descripcion": "Cena rápida alta en proteína.",
        "tiempo": "15 min", "calorias": "320 kcal", "dificultad": "Fácil",
        "tags": ["vegetariano", "alto-proteina", "rapido", "low-carb"],
        "ingredientes_base": ["huevo", "espinaca", "tomate", "cebolla", "queso", "champignon"],
        "ingredientes_detalle": ["3 huevos + 2 claras", "1 taza espinaca", "1/2 tomate", "1/4 cebolla", "30g queso fresco", "Ensalada verde para acompañar"],
        "pasos": ["Saltear verduras.", "Volcar huevos batidos, cocinar a fuego bajo.", "Doblar con queso y servir con ensalada."],
        "tip": "Fuego bajo = omelette esponjoso.",
    },
    {
        "id": "pasta-integral",
        "titulo": "Pasta integral con atún, tomate y olivas",
        "descripcion": "Clásico rendidor y saludable.",
        "tiempo": "20 min", "calorias": "510 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "rapido"],
        "ingredientes_base": ["pasta", "fideos", "atun", "tomate", "ajo", "oliva", "espinaca"],
        "ingredientes_detalle": ["250g pasta integral", "1 lata atún al agua", "2 tazas tomate triturado", "2 dientes ajo", "Puñado de olivas", "Albahaca y oliva"],
        "pasos": ["Hervir pasta al dente.", "Saltear ajo + tomate 8 min.", "Mezclar con atún, olivas y pasta."],
        "tip": "Guarda agua de cocción para ligar la salsa.",
    },
    {
        "id": "wok-verduras-tofu",
        "titulo": "Wok de tofu y verduras con salsa de soja y sésamo",
        "descripcion": "Vegano, crocante y lleno de color.",
        "tiempo": "20 min", "calorias": "400 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano"],
        "ingredientes_base": ["tofu", "brocoli", "zanahoria", "pimiento", "morrón", "arroz", "soja"],
        "ingredientes_detalle": ["400g tofu firme", "1 brócoli", "2 zanahorias", "1 morrón", "2 tazas arroz integral cocido", "Salsa de soja baja en sodio, jengibre, sésamo"],
        "pasos": ["Dorar tofu en cubos hasta crocante.", "Saltear verduras al wok.", "Mezclar con soja, jengibre y servir sobre arroz."],
        "tip": "Prensa el tofu 10 min para que quede crocante.",
    },
    {
        "id": "sopa-calabaza",
        "titulo": "Sopa crema de zapallo y zanahoria sin crema",
        "descripcion": "Dulce natural, ideal para noches frías.",
        "tiempo": "30 min", "calorias": "280 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano", "liviano"],
        "ingredientes_base": ["zapallo", "calabaza", "zanahoria", "cebolla", "ajo"],
        "ingredientes_detalle": ["1/2 zapallo", "3 zanahorias", "1 cebolla", "2 dientes ajo", "Caldo de verduras, cúrcuma, oliva"],
        "pasos": ["Saltear cebolla y ajo.", "Sumar zapallo y zanahoria + caldo, hervir 20 min.", "Licuar hasta cremoso."],
        "tip": "Toppings: semillas tostadas + yogur.",
    },
    {
        "id": "pollo-grill-ensalada",
        "titulo": "Pollo grill con ensalada griega",
        "descripcion": "Fresco, proteico y mediterráneo.",
        "tiempo": "20 min", "calorias": "450 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "low-carb", "mediterraneo"],
        "ingredientes_base": ["pollo", "tomate", "pepino", "cebolla", "queso", "oliva", "limon"],
        "ingredientes_detalle": ["2 pechugas pollo", "2 tomates", "1 pepino", "1/2 cebolla morada", "60g queso feta o fresco", "Olivas, orégano, oliva, limón"],
        "pasos": ["Grillar pollo 6 min por lado.", "Picar verduras estilo griego.", "Servir pollo sobre ensalada con feta."],
        "tip": "Marina el pollo 15 min en limón y orégano.",
    },
    {
        "id": "arroz-chaufa",
        "titulo": "Chaufa integral de pollo y verduras",
        "descripcion": "El favorito, en versión liviana.",
        "tiempo": "20 min", "calorias": "500 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "una-sarten"],
        "ingredientes_base": ["arroz", "pollo", "huevo", "zanahoria", "cebolla", "soja", "arvejas"],
        "ingredientes_detalle": ["2 tazas arroz integral cocido frío", "200g pollo en tiras", "2 huevos revueltos", "1 zanahoria", "Cebolla china, soja baja en sodio"],
        "pasos": ["Saltear pollo.", "Sumar verduras y arroz frío.", "Agregar huevo y soja, saltear fuerte."],
        "tip": "Arroz del día anterior = chaufa perfecto.",
    },
    {
        "id": "hamburguesa-lenteja",
        "titulo": "Hamburguesas de lentejas y avena",
        "descripcion": "Crocrantes por fuera, suaves por dentro.",
        "tiempo": "35 min", "calorias": "420 kcal", "dificultad": "Media",
        "tags": ["vegetariano", "vegano", "economico"],
        "ingredientes_base": ["lentejas", "avena", "cebolla", "zanahoria", "ajo"],
        "ingredientes_detalle": ["2 tazas lentejas cocidas", "1 taza avena", "1/2 cebolla", "1 zanahoria rallada", "Ajo, comino, pimentón"],
        "pasos": ["Procesar todo (textura gruesa).", "Formar medallones y refrigerar 15 min.", "Hornear o sartenear 5 min por lado."],
        "tip": "Sirve en pan integral con palta.",
    },
    {
        "id": "merluza-papillote",
        "titulo": "Merluza en papillote con verduras",
        "descripcion": "Cocción al vapor en papel, cero grasa agregada.",
        "tiempo": "25 min", "calorias": "380 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "liviano", "low-carb"],
        "ingredientes_base": ["pescado", "merluza", "zanahoria", "zucchini", "zapallito", "limon"],
        "ingredientes_detalle": ["4 filetes merluza", "1 zanahoria en juliana", "1 zucchini", "1 limón en rodajas", "Hierbas, sal, pimienta"],
        "pasos": ["Armar paquetes en papel manteca con verduras y pescado.", "Cerrar bien y hornear 15 min a 190°C.", "Abrir y servir con limón."],
        "tip": "Agrega tomate cherry para más jugo.",
    },
    {
        "id": "poke-atun",
        "titulo": "Poke de atún con arroz integral y mango",
        "descripcion": "Fresco estilo hawaiano.",
        "tiempo": "20 min", "calorias": "500 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "fresco"],
        "ingredientes_base": ["atun", "arroz", "mango", "palta", "aguacate", "pepino", "soja"],
        "ingredientes_detalle": ["300g atún fresco o 2 latas al agua", "2 tazas arroz integral", "1/2 mango", "1 palta", "1/2 pepino", "Soja baja en sodio, sésamo, lima"],
        "pasos": ["Cocinar arroz y enfriar.", "Cortar atún, mango, palta y pepino en cubos.", "Armar bowls y aliñar con soja y lima."],
        "tip": "Si usas atún crudo, que sea bien fresco.",
    },
    {
        "id": "tarta-verduras",
        "titulo": "Tarta integral de verduras y huevo",
        "descripcion": "Ideal para llevar al trabajo.",
        "tiempo": "45 min", "calorias": "460 kcal", "dificultad": "Media",
        "tags": ["vegetariano", "meal-prep"],
        "ingredientes_base": ["huevo", "espinaca", "zanahoria", "cebolla", "queso", "harina"],
        "ingredientes_detalle": ["1 tapa pascualina integral", "4 huevos", "2 tazas espinaca", "1 zanahoria rallada", "1 cebolla", "100g queso fresco"],
        "pasos": ["Saltear verduras.", "Batir huevos, mezclar con verduras y queso.", "Volcar en molde y hornear 30 min a 180°C."],
        "tip": "Rinde 4 porciones, freeza lo que sobre.",
    },
    {
        "id": "garbanzos-saltee",
        "titulo": "Garbanzos salteados con espinaca y tomate",
        "descripcion": "Proteína vegetal en 15 minutos.",
        "tiempo": "15 min", "calorias": "390 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano", "rapido", "economico"],
        "ingredientes_base": ["garbanzos", "espinaca", "tomate", "ajo", "cebolla"],
        "ingredientes_detalle": ["2 tazas garbanzos cocidos", "3 puñados espinaca", "1 taza tomate cherry", "2 dientes ajo", "Pimentón, comino, oliva"],
        "pasos": ["Dorar ajo y garbanzos 5 min.", "Sumar tomate hasta ablandar.", "Agregar espinaca y condimentos."],
        "tip": "Sirve con arroz o en tostadas integrales.",
    },
    {
        "id": "pechuga-rellena",
        "titulo": "Pechuga rellena de espinaca y queso",
        "descripcion": "Jugosa y con sorpresa verde.",
        "tiempo": "30 min", "calorias": "470 kcal", "dificultad": "Media",
        "tags": ["alto-proteina", "low-carb"],
        "ingredientes_base": ["pollo", "espinaca", "queso", "tomate"],
        "ingredientes_detalle": ["2 pechugas grandes", "2 tazas espinaca", "60g queso", "1 tomate", "Ajo, sal, pimienta"],
        "pasos": ["Abrir pechugas en bolsillo.", "Rellenar con espinaca, queso y tomate.", "Sellar y hornear 18 min a 190°C."],
        "tip": "Sujeta con palillos para que no se abra.",
    },
    {
        "id": "risotto-verduras",
        "titulo": "Risotto integral de verduras",
        "descripcion": "Cremoso sin manteca (con queso fresco).",
        "tiempo": "40 min", "calorias": "520 kcal", "dificultad": "Media",
        "tags": ["vegetariano"],
        "ingredientes_base": ["arroz", "zanahoria", "zapallito", "zucchini", "cebolla", "queso"],
        "ingredientes_detalle": ["1 1/2 taza arroz integral", "1 zucchini", "1 zanahoria", "1 cebolla", "50g queso fresco rallado", "Caldo de verduras"],
        "pasos": ["Saltear cebolla y arroz.", "Agregar caldo de a poco 30 min.", "Terminar con verduras y queso."],
        "tip": "Revuelve seguido para que quede cremoso.",
    },
    {
        "id": "ensalada-quinoa-medit",
        "titulo": "Ensalada mediterránea de quinoa",
        "descripcion": "Sin cocción larga, todo picado.",
        "tiempo": "20 min", "calorias": "410 kcal", "dificultad": "Fácil",
        "tags": ["vegetariano", "sin-gluten", "fresco", "meal-prep"],
        "ingredientes_base": ["quinoa", "tomate", "pepino", "cebolla", "oliva", "limon"],
        "ingredientes_detalle": ["1 taza quinoa cocida", "1 taza tomate cherry", "1 pepino", "1/4 cebolla morada", "Olivas, feta opcional, oliva, limón"],
        "pasos": ["Cocinar quinoa si no está lista.", "Picar todo.", "Mezclar y aliñar."],
        "tip": "Dura 3 días en heladera.",
    },
    {
        "id": "carne-pimientos",
        "titulo": "Tiras de carne magra con pimientos y cebolla",
        "descripcion": "Estilo fajita, sin tortilla (o con).",
        "tiempo": "25 min", "calorias": "480 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "low-carb"],
        "ingredientes_base": ["carne", "pimiento", "morrón", "cebolla"],
        "ingredientes_detalle": ["500g bola de lomo en tiras", "2 morrones", "1 cebolla grande", "Ajo, comino, pimentón"],
        "pasos": ["Sellar carne fuerte y reservar.", "Saltear pimientos y cebolla.", "Unir todo 3 min."],
        "tip": "Sirve con ensalada o arroz integral.",
    },
    {
        "id": "cazuela-pollo",
        "titulo": "Cazuela liviana de pollo y verduras",
        "descripcion": "Hogar y cuchara, versión saludable.",
        "tiempo": "40 min", "calorias": "450 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "una-olla"],
        "ingredientes_base": ["pollo", "papa", "patata", "zanahoria", "cebolla", "zapallo"],
        "ingredientes_detalle": ["4 presas pollo sin piel", "2 papas", "2 zanahorias", "1 cebolla", "2 tazas zapallo", "Caldo, laurel, sal"],
        "pasos": ["Dorar pollo.", "Sumar verduras + caldo.", "Cocinar 25 min a fuego medio."],
        "tip": "Desgrasa el caldo en frío si la haces antes.",
    },
    {
        "id": "buddha-veggie",
        "titulo": "Buddha bowl de garbanzos crocantes",
        "descripcion": "El bowl veggie más instagrameable y rico.",
        "tiempo": "30 min", "calorias": "480 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano"],
        "ingredientes_base": ["garbanzos", "batata", "boniato", "espinaca", "palta", "arroz", "quinoa"],
        "ingredientes_detalle": ["1 1/2 taza garbanzos", "1 batata en cubos", "2 tazas espinaca", "1/2 palta", "1 taza quinoa cocida", "Tahini, limón, pimentón"],
        "pasos": ["Hornear garbanzos + batata con pimentón 25 min.", "Armar bowl sobre quinoa.", "Aderezar con tahini-limón."],
        "tip": "El tahini se aligera con agua tibia.",
    },
    {
        "id": "frittata-horno",
        "titulo": "Frittata al horno con verduras de estación",
        "descripcion": "Tortilla alta sin fritura.",
        "tiempo": "30 min", "calorias": "350 kcal", "dificultad": "Fácil",
        "tags": ["vegetariano", "low-carb", "meal-prep"],
        "ingredientes_base": ["huevo", "zucchini", "zapallito", "tomate", "cebolla", "queso"],
        "ingredientes_detalle": ["6 huevos", "1 zucchini", "1 taza cherry", "1/2 cebolla", "50g queso", "Sal, pimienta, orégano"],
        "pasos": ["Saltear verduras.", "Volcar huevos batidos encima.", "Hornear 15 min a 180°C."],
        "tip": "Riquísima fría al día siguiente.",
    },
    {
        "id": "pollo-teriyaki",
        "titulo": "Pollo teriyaki casero light con brócoli",
        "descripcion": "Dulce-salado sin azúcar refinada (con miel).",
        "tiempo": "25 min", "calorias": "490 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina"],
        "ingredientes_base": ["pollo", "brocoli", "arroz", "soja", "miel", "ajo"],
        "ingredientes_detalle": ["500g pollo en cubos", "1 brócoli", "2 tazas arroz integral", "3 cda soja baja en sodio", "1 cda miel", "Ajo y jengibre"],
        "pasos": ["Saltear pollo.", "Sumar brócoli + salsa (soja+miel+ajo).", "Servir sobre arroz."],
        "tip": "Espesa la salsa con 1 cdta maicena.",
    },
]

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ---------------------------------------------------------------- utilidades

def normalizar(txt: str) -> str:
    txt = txt.lower().strip()
    txt = "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")
    return txt


def parsear_ingredientes(raw) -> List[str]:
    """Acepta string separado por comas/saltos o lista. Limpia y deduplica."""
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r"[,;\n]+", str(raw or ""))
    out = []
    for it in items:
        it = str(it).strip().lower()
        it = re.sub(r"\s+", " ", it)
        if len(it) >= 2:
            out.append(it)
    # dedup preservando orden
    vistos, final = set(), []
    for i in out:
        if i not in vistos:
            vistos.add(i)
            final.append(i)
    return final[:30]


def score_receta(receta, ingredientes_norm: List[str]) -> int:
    base = [normalizar(b) for b in receta["ingredientes_base"]]
    puntaje = 0
    for ing in ingredientes_norm:
        for b in base:
            if ing in b or b in ing:
                puntaje += 3
                break
    # bonus variedad / saludable
    puntaje += len(set(base)) * 0.1
    return puntaje


def cumple_preferencias(receta, prefs: List[str]) -> bool:
    p = [normalizar(x) for x in (prefs or [])]
    tags = [normalizar(t) for t in receta.get("tags", [])]
    txt = " ".join(tags + [normalizar(receta["titulo"]), normalizar(receta["descripcion"])])
    if any("vegetar" in x or x == "veggie" for x in p):
        if not any("vegetar" in t or "vegano" in t for t in tags):
            return False
    if any("vegan" in x for x in p):
        if "vegano" not in tags:
            return False
    if any("gluten" in x for x in p):
        if not ("sin-gluten" in tags or "sin gluten" in txt):
            return False
    if any("rapida" in x or "rapido" in x or "15" in x or "express" in x for x in p):
        if "15 min" not in receta["tiempo"] and "20 min" not in receta["tiempo"]:
            # no excluyente, solo desprioriza
            pass
    return True


def google_url(q: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(q + " receta saludable")


def youtube_url(q: str) -> str:
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q + " receta saludable")


def buscar_themealdb(ingrediente: str, timeout=6):
    """Busca recetas reales en TheMealDB (API gratuita, sin key). Devuelve lista dict."""
    try:
        q = urllib.parse.quote_plus(ingrediente.strip())
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "semana-saludable/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        meals = data.get("meals") or []
        return [
            {
                "nombre": m.get("strMeal", ""),
                "foto": m.get("strMealThumb", ""),
                "fuente": f"https://www.themealdb.com/meal/{m.get('idMeal','')}",
                "ingrediente_match": ingrediente,
            }
            for m in meals[:4]
        ]
    except Exception:
        return []


def lookup_themealdb_detalle(nombre: str, timeout=6):
    try:
        q = urllib.parse.quote_plus(nombre)
        url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "semana-saludable/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        meals = data.get("meals") or []
        if not meals:
            return None
        return meals[0]
    except Exception:
        return None


# ---------------------------------------------------------------- modelos

class GenerateIn(BaseModel):
    ingredientes: object = Field(default_factory=list)  # lista o string
    dias: int = Field(default=7, ge=1, le=7)
    preferencias: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------- endpoints

@app.get("/api/health")
def health():
    return {"ok": True, "recetas": len(RECETAS)}


@app.get("/api/search")
def search(q: str = Query(default="", min_length=1)):
    """Proxy de búsqueda real en internet (TheMealDB + links Google/YouTube)."""
    resultados = buscar_themealdb(q)
    return {
        "query": q,
        "resultados_internet": resultados,
        "google": google_url(q),
        "youtube": youtube_url(q),
    }


@app.post("/api/generate")
def generate(body: GenerateIn):
    ingredientes = parsear_ingredientes(body.ingredientes)
    dias = max(1, min(7, int(body.dias or 7)))
    prefs = body.preferencias or []

    ing_norm = [normalizar(i) for i in ingredientes]

    candidatas = [r for r in RECETAS if cumple_preferencias(r, prefs)] or list(RECETAS)
    rankeadas = sorted(candidatas, key=lambda r: score_receta(r, ing_norm), reverse=True)

    # diversificar: no repetir proteína base dos días seguidos si hay variedad
    menu, usadas = [], set()
    pool = rankeadas + rankeadas  # permite repetir si dias > recetas únicas
    idx = 0
    for d in range(dias):
        elegida = None
        for cand in pool:
            if cand["id"] not in usadas or len(usadas) >= len(candidatas):
                # evita repetir id consecutivo
                if menu and menu[-1]["id"] == cand["id"]:
                    continue
                elegida = cand
                break
        if elegida is None:
            elegida = random.choice(rankeadas)
        usadas.add(elegida["id"])
        menu.append(elegida)
        # rota el pool para variar
        pool = [c for c in pool if c["id"] != elegida["id"]] + [elegida]
        idx += 1

    # enriquecer cada día
    semana = []
    for i, rec in enumerate(menu):
        usados = []
        extras = []
        for b in rec["ingredientes_base"]:
            nb = normalizar(b)
            if any((ing in nb or nb in ing) for ing in ing_norm):
                usados.append(b)
        # ingredientes extra = detalle que no matchea (para lista de compras)
        detalle_norm = [normalizar(x) for x in rec["ingredientes_detalle"]]
        semana.append(
            {
                "dia": DIAS[i],
                "dia_num": i + 1,
                "id": rec["id"],
                "titulo": rec["titulo"],
                "descripcion": rec["descripcion"],
                "tiempo": rec["tiempo"],
                "calorias": rec["calorias"],
                "dificultad": rec["dificultad"],
                "tags": rec["tags"],
                "ingredientes_usan_tuyos": sorted(set(usados)) or ingredientes[:3],
                "ingredientes_detalle": rec["ingredientes_detalle"],
                "pasos": rec["pasos"],
                "tip_saludable": rec["tip"],
                "ver_en_google": google_url(rec["titulo"]),
                "ver_en_youtube": youtube_url(rec["titulo"]),
            }
        )

    # búsqueda real en internet para los 2 primeros ingredientes (liviano)
    inspiracion = []
    for ing in ingredientes[:2]:
        for m in buscar_themealdb(ing):
            m["link_google"] = google_url(m["nombre"])
            inspiracion.append(m)
        if len(inspiracion) >= 6:
            break

    # lista de compras agregada (conteo simple de líneas únicas)
    compras_map = {}
    for dia in semana:
        for item in dia["ingredientes_detalle"]:
            key = item.strip()
            compras_map[key] = compras_map.get(key, 0) + 1
    lista_compras = sorted(compras_map.keys())

    return {
        "ingredientes_recibidos": ingredientes,
        "dias": dias,
        "preferencias": prefs,
        "menu": semana,
        "lista_compras": lista_compras,
        "inspiracion_internet": inspiracion,
        "nota": "Tus ingredientes son la base, no el límite: cada receta suma más alimentos para que sea completa y saludable.",
    }


# Para `vercel dev` / uvicorn local
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
