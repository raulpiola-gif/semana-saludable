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
import base64
import hashlib
import concurrent.futures
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
    {
        "id": "burrito-bowl",
        "titulo": "Burrito bowl mexicano con pollo",
        "descripcion": "Todo el sabor del burrito, sin tortilla y en bowl.",
        "tiempo": "30 min", "calorias": "530 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "sin-gluten"],
        "ingredientes_base": ["pollo", "arroz", "porotos", "frijoles", "tomate", "palta", "aguacate", "maiz", "choclo", "limon"],
        "ingredientes_detalle": ["400g pollo en tiras", "2 tazas arroz integral", "1 1/2 taza porotos cocidos", "1 taza tomate en cubos", "1 palta", "1 taza choclo", "Lima, comino, pimentón"],
        "pasos": ["Condimentar el pollo con comino y pimentón, grillar.", "Calentar porotos y choclo.", "Armar bowls con arroz y todo encima, terminar con lima."],
        "tip": "El yogur natural reemplaza la crema ácida.",
    },
    {
        "id": "pasta-pesto-espinaca",
        "titulo": "Pasta con pesto de espinaca y nuez",
        "descripcion": "Pesto verde sin albahaca: barato y rendidor.",
        "tiempo": "20 min", "calorias": "510 kcal", "dificultad": "Fácil",
        "tags": ["vegetariano", "rapido"],
        "ingredientes_base": ["pasta", "fideos", "espinaca", "nuez", "ajo", "queso", "oliva"],
        "ingredientes_detalle": ["250g pasta integral", "3 tazas espinaca", "1/2 taza nueces", "1 diente ajo", "40g queso rallado", "Aceite de oliva, sal"],
        "pasos": ["Hervir la pasta.", "Licuar espinaca, nueces, ajo, queso y oliva.", "Mezclar con la pasta y un poco de agua de cocción."],
        "tip": "Tuesta las nueces 3 min para más sabor.",
    },
    {
        "id": "carne-brocoli-oriental",
        "titulo": "Salteado oriental de carne con brócoli",
        "descripcion": "Estilo chifa, listo en una sartén.",
        "tiempo": "25 min", "calorias": "490 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "una-sarten"],
        "ingredientes_base": ["carne", "brocoli", "zanahoria", "arroz", "soja", "ajo"],
        "ingredientes_detalle": ["500g carne en tiras finas", "1 brócoli", "2 zanahorias", "2 tazas arroz integral cocido", "3 cda soja baja en sodio", "Ajo, jengibre"],
        "pasos": ["Sellar la carne a fuego fuerte y reservar.", "Saltear brócoli y zanahoria 4 min.", "Volver la carne con soja, ajo y jengibre. Servir sobre arroz."],
        "tip": "Corta la carne bien fina y contra la fibra.",
    },
    {
        "id": "cuscus-verduras",
        "titulo": "Cuscús con verduras asadas y garbanzos",
        "descripcion": "Dulce-salado con comino y pasas opcional.",
        "tiempo": "30 min", "calorias": "450 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano"],
        "ingredientes_base": ["cuscus", "garbanzos", "zapallo", "calabaza", "pimiento", "morrón", "cebolla"],
        "ingredientes_detalle": ["1 1/2 taza cuscús", "1 1/2 taza garbanzos cocidos", "2 tazas zapallo en cubos", "1 morrón", "1 cebolla", "Comino, pimentón, oliva"],
        "pasos": ["Asar verduras con especias 25 min a 200°C.", "Hidratar el cuscús con agua hirviendo 5 min.", "Mezclar todo con garbanzos y oliva."],
        "tip": "Agrega pasas de uva y menta para versión marroquí.",
    },
    {
        "id": "tortilla-papa-horno",
        "titulo": "Tortilla de papas al horno sin fritura",
        "descripcion": "La clásica, liviana y alta.",
        "tiempo": "50 min", "calorias": "420 kcal", "dificultad": "Media",
        "tags": ["vegetariano", "sin-gluten"],
        "ingredientes_base": ["papa", "patata", "huevo", "cebolla"],
        "ingredientes_detalle": ["4 papas en rodajas finas", "6 huevos", "1 cebolla", "2 cda aceite de oliva", "Sal"],
        "pasos": ["Mezclar papas y cebolla con oliva y sal, hornear 25 min.", "Batir huevos y unir con las papas.", "Volcar en sartén apta y hornear 20 min más."],
        "tip": "Deja reposar 10 min antes de cortar.",
    },
    {
        "id": "pollo-limon-romero",
        "titulo": "Pollo al limón con papas al romero",
        "descripcion": "Horno y listo: marinado cítrico.",
        "tiempo": "40 min", "calorias": "520 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "una-bandeja"],
        "ingredientes_base": ["pollo", "papa", "patata", "limon", "ajo"],
        "ingredientes_detalle": ["4 presas de pollo", "4 papas en cuñas", "2 limones", "3 dientes ajo", "Romero, oliva, sal, pimienta"],
        "pasos": ["Marinar pollo 15 min en limón, ajo y romero.", "Hornear todo junto 30 min a 200°C.", "Dorar 5 min más si hace falta."],
        "tip": "Usa presas con hueso: quedan más jugosas.",
    },
    {
        "id": "cesar-saludable",
        "titulo": "Ensalada César liviana con pollo",
        "descripcion": "Aderezo de yogur: cremoso sin mayonesa.",
        "tiempo": "25 min", "calorias": "430 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "fresco"],
        "ingredientes_base": ["pollo", "lechuga", "yogur", "queso", "ajo", "limon"],
        "ingredientes_detalle": ["2 pechugas grilladas", "1 lechuga romana", "1 yogur natural", "30g queso rallado", "1 diente ajo", "Limón, mostaza, sal"],
        "pasos": ["Grillar el pollo y cortarlo.", "Licuar yogur, ajo, limón y mostaza.", "Armar con lechuga, pollo, queso y aderezo."],
        "tip": "Crutones integrales caseros al horno.",
    },
    {
        "id": "guiso-lentejas",
        "titulo": "Guiso de lentejas con verduras",
        "descripcion": "Cuchara, hierro y comfort food.",
        "tiempo": "45 min", "calorias": "480 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano", "economico", "una-olla"],
        "ingredientes_base": ["lentejas", "zanahoria", "papa", "patata", "cebolla", "tomate"],
        "ingredientes_detalle": ["2 tazas lentejas", "2 zanahorias", "2 papas", "1 cebolla", "1 taza tomate triturado", "Laurel, pimentón, comino"],
        "pasos": ["Saltear cebolla y condimentos.", "Sumar verduras, lentejas y agua.", "Cocinar 30 min hasta tierno."],
        "tip": "Más rico al día siguiente.",
    },
    {
        "id": "pescado-pure-coliflor",
        "titulo": "Pescado a la plancha con puré de coliflor",
        "descripcion": "Puré cremoso bajo en carbohidratos.",
        "tiempo": "25 min", "calorias": "390 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "low-carb", "liviano"],
        "ingredientes_base": ["pescado", "merluza", "coliflor", "limon", "ajo"],
        "ingredientes_detalle": ["4 filetes de pescado", "1 coliflor", "2 dientes ajo", "1 limón", "Oliva, sal, pimienta"],
        "pasos": ["Hervir coliflor 12 min y pisar con oliva y ajo.", "Sellar el pescado 3 min por lado.", "Servir con limón."],
        "tip": "Nuez moscada al puré, queda increíble.",
    },
    {
        "id": "wrap-atun-palta",
        "titulo": "Wrap integral de atún, palta y verduras",
        "descripcion": "Sin cocción, ideal para llevar.",
        "tiempo": "15 min", "calorias": "450 kcal", "dificultad": "Fácil",
        "tags": ["pescado", "rapido", "fresco"],
        "ingredientes_base": ["atun", "palta", "aguacate", "tortilla", "lechuga", "tomate"],
        "ingredientes_detalle": ["2 latas atún al agua", "1 palta", "4 tortillas integrales", "Hojas de lechuga", "1 tomate", "Limón, sal"],
        "pasos": ["Pisar palta con limón y sal.", "Mezclar con atún escurrido.", "Rellenar tortillas con lechuga y tomate."],
        "tip": "Tuesta el wrap 1 min por lado para sellarlo.",
    },
    {
        "id": "sopa-pollo-verduras",
        "titulo": "Sopa de pollo con verduras y fideos integrales",
        "descripcion": "Caldo casero que abraza.",
        "tiempo": "40 min", "calorias": "350 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina", "liviano", "una-olla"],
        "ingredientes_base": ["pollo", "zanahoria", "cebolla", "papa", "patata", "pasta", "fideos"],
        "ingredientes_detalle": ["2 pechugas o 4 muslos sin piel", "2 zanahorias", "1 cebolla", "2 papas", "100g fideos integrales", "Apio, laurel, sal"],
        "pasos": ["Hervir pollo con verduras 25 min.", "Desmenuzar el pollo.", "Sumar fideos y cocinar 8 min."],
        "tip": "Congela en porciones para la semana.",
    },
    {
        "id": "albondigas-pollo",
        "titulo": "Albóndigas de pollo en salsa de tomate con arroz",
        "descripcion": "Tiernas al horno, salsa casera.",
        "tiempo": "40 min", "calorias": "530 kcal", "dificultad": "Media",
        "tags": ["alto-proteina"],
        "ingredientes_base": ["pollo", "tomate", "arroz", "cebolla", "ajo"],
        "ingredientes_detalle": ["500g pollo picado", "2 tazas tomate triturado", "2 tazas arroz integral cocido", "1/2 cebolla rallada", "Ajo, orégano, sal"],
        "pasos": ["Mezclar pollo con cebolla y formar bolitas.", "Hornear 15 min a 200°C.", "Terminar 10 min en la salsa de tomate."],
        "tip": "Manos mojadas = albóndigas perfectas.",
    },
    {
        "id": "ensalada-garbanzos-griega",
        "titulo": "Ensalada griega de garbanzos",
        "descripcion": "Sin cocción, lista en 15 minutos.",
        "tiempo": "15 min", "calorias": "400 kcal", "dificultad": "Fácil",
        "tags": ["vegetariano", "rapido", "fresco", "meal-prep"],
        "ingredientes_base": ["garbanzos", "tomate", "pepino", "cebolla", "queso", "oliva"],
        "ingredientes_detalle": ["2 tazas garbanzos cocidos", "1 taza tomate cherry", "1 pepino", "1/4 cebolla morada", "60g queso feta o fresco", "Olivas, orégano, oliva, limón"],
        "pasos": ["Picar todo en cubos.", "Mezclar con garbanzos.", "Aliñar con oliva, limón y orégano."],
        "tip": "Mejor fría de heladera.",
    },
    {
        "id": "revuelto-tofu",
        "titulo": "Revuelto de tofu con cúrcuma y verduras",
        "descripcion": "El 'huevo revuelto' vegano.",
        "tiempo": "15 min", "calorias": "350 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano", "rapido"],
        "ingredientes_base": ["tofu", "espinaca", "tomate", "cebolla", "champignon"],
        "ingredientes_detalle": ["400g tofu firme desmenuzado", "2 puñados espinaca", "1 tomate", "1/2 cebolla", "4 champiñones", "Cúrcuma, comino, sal negra si hay"],
        "pasos": ["Saltear cebolla y champiñones.", "Sumar tofu con cúrcuma 5 min.", "Agregar tomate y espinaca al final."],
        "tip": "La sal negra le da gusto a huevo.",
    },
    {
        "id": "lasana-zucchini",
        "titulo": "Lasaña de zucchini sin pasta",
        "descripcion": "Capas y queso, versión low-carb.",
        "tiempo": "45 min", "calorias": "420 kcal", "dificultad": "Media",
        "tags": ["vegetariano", "low-carb"],
        "ingredientes_base": ["zucchini", "zapallito", "tomate", "queso", "cebolla"],
        "ingredientes_detalle": ["3 zucchinis en láminas", "2 tazas salsa de tomate", "200g queso fresco", "50g queso rallado", "Albahaca, orégano"],
        "pasos": ["Grillar láminas de zucchini.", "Armar capas con salsa y queso.", "Hornear 25 min a 190°C y gratinar."],
        "tip": "Sala el zucchini 10 min y seca: no se aguachenta.",
    },
    {
        "id": "pollo-miel-mostaza",
        "titulo": "Pollo con miel y mostaza + ensalada verde",
        "descripcion": "Glaseado dorado irresistible.",
        "tiempo": "30 min", "calorias": "470 kcal", "dificultad": "Fácil",
        "tags": ["alto-proteina"],
        "ingredientes_base": ["pollo", "miel", "mostaza", "lechuga", "limon"],
        "ingredientes_detalle": ["4 pechugas", "2 cda miel", "2 cda mostaza", "Ensalada verde", "Ajo, sal, pimienta"],
        "pasos": ["Mezclar miel, mostaza y ajo.", "Pincelar el pollo y hornear 22 min.", "Servir con ensalada verde."],
        "tip": "Pincela a mitad de cocción para más brillo.",
    },
    {
        "id": "croquetas-arroz",
        "titulo": "Croquetas de arroz y espinaca al horno",
        "descripcion": "Reciclaje delicioso del arroz de ayer.",
        "tiempo": "40 min", "calorias": "430 kcal", "dificultad": "Media",
        "tags": ["vegetariano", "economico"],
        "ingredientes_base": ["arroz", "espinaca", "huevo", "queso"],
        "ingredientes_detalle": ["2 tazas arroz cocido", "2 tazas espinaca salteada", "2 huevos", "80g queso en cubos", "Pan rallado integral"],
        "pasos": ["Mezclar arroz, espinaca y huevo.", "Formar bolitas con queso adentro.", "Rebozar y hornear 20 min."],
        "tip": "Sirve con salsa de tomate caliente.",
    },
    {
        "id": "tabule-quinoa",
        "titulo": "Tabulé de quinoa con hierbas y tomate",
        "descripcion": "Fresco estilo libanés, lleno de perejil.",
        "tiempo": "20 min", "calorias": "380 kcal", "dificultad": "Fácil",
        "tags": ["vegano", "vegetariano", "fresco", "sin-gluten"],
        "ingredientes_base": ["quinoa", "tomate", "pepino", "limon", "cebolla"],
        "ingredientes_detalle": ["1 taza quinoa cocida", "2 tomates", "1/2 pepino", "1 atado perejil", "Menta fresca, limón, oliva"],
        "pasos": ["Picar hierbas y verduras bien chico.", "Mezclar con quinoa fría.", "Aliñar generoso con limón y oliva."],
        "tip": "El secreto es mucho perejil y buen limón.",
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
                "id": m.get("idMeal", ""),
                "nombre": m.get("strMeal", ""),
                "foto": m.get("strMealThumb", ""),
                "fuente": f"https://www.themealdb.com/meal/{m.get('idMeal','')}",
                "ingrediente_match": ingrediente,
            }
            for m in meals[:6]
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


# ---------------------------------------------------------------- internet
# Glosario ES->EN para buscar ingredientes del usuario en TheMealDB (en inglés).
ES_EN = {
    "pollo": "chicken", "arroz": "rice", "huevo": "egg", "huevos": "egg",
    "leche": "milk", "queso": "cheese", "tomate": "tomato", "tomates": "tomato",
    "cebolla": "onion", "ajo": "garlic", "papa": "potato", "patata": "potato",
    "papas": "potato", "zanahoria": "carrot", "zanahorias": "carrot",
    "carne": "beef", "cerdo": "pork", "pescado": "fish", "atun": "tuna",
    "atún": "tuna", "salmon": "salmon", "salmón": "salmon", "merluza": "hake",
    "camaron": "shrimp", "camarones": "shrimp", "tofu": "tofu",
    "espinaca": "spinach", "espinacas": "spinach", "lechuga": "lettuce",
    "brocoli": "broccoli", "brócoli": "broccoli", "coliflor": "cauliflower",
    "zapallo": "pumpkin", "calabaza": "pumpkin", "choclo": "corn", "maiz": "corn",
    "maíz": "corn", "arvejas": "peas", "arveja": "peas", "porotos": "beans",
    "frijoles": "beans", "poroto": "beans", "lentejas": "lentils", "lenteja": "lentils",
    "garbanzos": "chickpeas", "garbanzo": "chickpeas", "palta": "avocado",
    "aguacate": "avocado", "limon": "lemon", "limón": "lemon", "lima": "lime",
    "pasta": "pasta", "fideos": "pasta", "tallarines": "pasta",
    "pimiento": "pepper", "morron": "pepper", "morrón": "pepper",
    "pepino": "cucumber", "manzana": "apple", "banana": "banana", "mango": "mango",
    "miel": "honey", "harina": "flour", "avena": "oats", "manteca": "butter",
    "mantequilla": "butter", "yogur": "yogurt", "yogurt": "yogurt",
    "batata": "sweet potato", "boniato": "sweet potato", "berenjena": "eggplant",
    "zucchini": "zucchini", "zapallito": "zucchini", "repollo": "cabbage",
    "apio": "celery", "jengibre": "ginger", "curry": "curry", "comino": "cumin",
    "pimenton": "paprika", "pimentón": "paprika", "oregano": "oregano",
    "orégano": "oregano", "perejil": "parsley", "albahaca": "basil",
    "canela": "cinnamon", "mostaza": "mustard", "soja": "soy sauce",
    "vinagre": "vinegar", "pan": "bread", "quinoa": "quinoa", "couscous": "couscous",
    "cuscus": "couscous", "champignon": "mushroom", "champiñones": "mushroom",
    "hongos": "mushroom", "nuez": "walnuts", "nueces": "walnuts",
    "almendra": "almonds", "mani": "peanuts", "maní": "peanuts", "coco": "coconut",
    "chocolate": "chocolate", "vainilla": "vanilla", "naranja": "orange",
    "frutilla": "strawberry", "ananá": "pineapple", "anana": "pineapple",
    "pera": "pear", "durazno": "peach", "uva": "grapes", "sandia": "watermelon",
    "pavo": "turkey", "cordero": "lamb", "pato": "duck", "jamon": "ham",
    "salchicha": "sausage", "chorizo": "sausage", "panceta": "bacon",
    "crema": "cream", "ricota": "ricotta", "mozzarella": "mozzarella",
    "parmesano": "parmesan", "feta": "feta", "aceituna": "olives",
    "olivas": "olives", "aceitunas": "olives", "menta": "mint", "romero": "rosemary",
    "tomillo": "thyme", "laurel": "bay leaf", "cilantro": "coriander",
    "kale": "kale", "rucula": "rocket", "rúcula": "rocket",
}

# Glosario EN->ES para mostrar las recetas de internet en español.
# Traducción automática aproximada (frases largas primero).
EN_ES = {
    "olive oil": "aceite de oliva", "vegetable oil": "aceite vegetal",
    "sesame oil": "aceite de sésamo", "soy sauce": "salsa de soja",
    "lemon juice": "jugo de limón", "orange juice": "jugo de naranja",
    "tomato puree": "puré de tomate", "tomato paste": "extracto de tomate",
    "chopped tomatoes": "tomates picados", "tinned tomatoes": "tomates en lata",
    "chicken breast": "pechuga de pollo", "chicken stock": "caldo de pollo",
    "chicken thighs": "muslos de pollo", "minced beef": "carne picada",
    "minced pork": "cerdo picado", "ground beef": "carne picada",
    "red pepper": "morrón rojo", "green pepper": "morrón verde",
    "yellow pepper": "morrón amarillo", "black pepper": "pimienta negra",
    "spring onions": "cebollas de verdeo", "spring onion": "cebolla de verdeo",
    "bay leaf": "hoja de laurel", "bay leaves": "hojas de laurel",
    "baking powder": "polvo de hornear", "corn flour": "maicena",
    "cornstarch": "maicena", "icing sugar": "azúcar impalpable",
    "dark chocolate": "chocolate amargo", "coconut milk": "leche de coco",
    "peanut butter": "manteca de maní", "red wine": "vino tinto",
    "white wine": "vino blanco", "green beans": "chauchas",
    "kidney beans": "porotos colorados", "black beans": "porotos negros",
    "white beans": "porotos blancos", "red lentils": "lentejas rojas",
    "long grain rice": "arroz grano largo", "jasmine rice": "arroz jazmín",
    "lemon zest": "ralladura de limón", "orange zest": "ralladura de naranja",
    "sour cream": "crema ácida", "greek yogurt": "yogur griego",
    "heavy cream": "crema", "double cream": "crema",
    "sea salt": "sal marina", "chicken": "pollo", "beef": "carne", "pork": "cerdo",
    "lamb": "cordero", "turkey": "pavo", "duck": "pato", "ham": "jamón",
    "bacon": "panceta", "sausage": "chorizo", "fish": "pescado",
    "salmon": "salmón", "tuna": "atún", "hake": "merluza", "cod": "bacalao",
    "shrimp": "camarones", "prawns": "langostinos", "mussels": "mejillones",
    "squid": "calamar", "octopus": "pulpo", "egg": "huevo", "eggs": "huevos",
    "rice": "arroz", "pasta": "pasta", "spaghetti": "espaguetis",
    "noodles": "fideos", "bread": "pan", "flour": "harina", "milk": "leche",
    "cheese": "queso", "butter": "manteca", "oil": "aceite", "garlic": "ajo",
    "onion": "cebolla", "onions": "cebollas", "tomato": "tomate",
    "tomatoes": "tomates", "potato": "papa", "potatoes": "papas",
    "carrot": "zanahoria", "carrots": "zanahorias", "broccoli": "brócoli",
    "spinach": "espinaca", "lettuce": "lechuga", "cucumber": "pepino",
    "pepper": "pimiento", "peppers": "morrones", "mushroom": "champiñón",
    "mushrooms": "champiñones", "corn": "choclo", "peas": "arvejas",
    "beans": "porotos", "bean": "poroto", "lentils": "lentejas",
    "lentil": "lenteja", "chickpeas": "garbanzos", "chickpea": "garbanzo",
    "avocado": "palta", "lemon": "limón", "lime": "lima", "orange": "naranja",
    "apple": "manzana", "banana": "banana", "pineapple": "ananá",
    "mango": "mango", "strawberry": "frutilla", "strawberries": "frutillas",
    "salt": "sal", "sugar": "azúcar", "honey": "miel", "soup": "sopa",
    "salad": "ensalada", "stew": "guiso", "curry": "curry", "pie": "tarta",
    "cake": "torta", "grilled": "grillado", "baked": "al horno", "bake": "hornear",
    "fried": "frito", "roasted": "asado", "roast": "asado", "boil": "hervir",
    "chopped": "picado", "sliced": "en rodajas", "diced": "en cubos",
    "grated": "rallado", "minced": "picado", "melted": "derretido",
    "beaten": "batido", "shredded": "desmenuzado", "sauce": "salsa",
    "with": "con", "and": "y", "of": "de", "cup": "taza", "cups": "tazas",
    "tablespoon": "cucharada", "teaspoon": "cucharadita", "clove": "diente",
    "cloves": "dientes", "fresh": "fresco", "water": "agua", "heat": "calentar",
    "add": "agregar", "mix": "mezclar", "stir": "revolver", "cook": "cocinar",
    "serve": "servir", "minutes": "minutos", "minute": "minuto", "hour": "hora",
    "until": "hasta que", "golden": "dorado", "brown": "dorado", "oven": "horno",
    "pan": "sartén", "pot": "olla", "preheat": "precalentar", "cream": "crema",
    "yogurt": "yogur", "mustard": "mostaza", "vinegar": "vinagre",
    "wine": "vino", "white": "blanco", "red": "rojo", "black": "negro",
    "green": "verde", "powder": "en polvo", "ground": "molido", "cumin": "comino",
    "paprika": "pimentón", "oregano": "orégano", "basil": "albahaca",
    "parsley": "perejil", "cinnamon": "canela", "ginger": "jengibre",
    "coconut": "coco", "chocolate": "chocolate", "vanilla": "vainilla",
    "peanut": "maní", "almond": "almendra", "walnuts": "nueces", "walnut": "nuez",
    "vegetable": "verdura", "vegetables": "verduras", "stock": "caldo",
    "broth": "caldo", "juice": "jugo", "hot": "caliente", "cold": "frío",
    "large": "grande", "small": "pequeño", "medium": "mediano", "whole": "entero",
    "half": "medio", "can": "lata", "tinned": "en lata", "feta": "feta",
    "mozzarella": "mozzarella", "parmesan": "parmesano", "cheddar": "cheddar",
    "olives": "aceitunas", "olive": "aceituna", "sesame": "sésamo",
    "chili": "ají", "celery": "apio", "cabbage": "repollo",
    "cauliflower": "coliflor", "eggplant": "berenjena", "zucchini": "zucchini",
    "pumpkin": "zapallo", "asparagus": "espárragos", "coriander": "cilantro",
    "mint": "menta", "thyme": "tomillo", "rosemary": "romero",
    "tofu": "tofu", "oats": "avena", "couscous": "cuscús", "quinoa": "quinoa",
    "yeast": "levadura", "coffee": "café", "tea": "té", "seafood": "mariscos",
    "vegetarian": "vegetariana", "vegan": "vegana", "starter": "entrada",
    "side": "guarnición", "dessert": "postre", "miscellaneous": "varios",
    "thai": "tailandés", "italian": "italiano", "mexican": "mexicano",
    "chinese": "chino", "japanese": "japonés", "indian": "indio",
    "jamaican": "jamaiquino", "greek": "griego", "french": "francés",
    "spanish": "español", "american": "americano", "british": "británico",
    "moroccan": "marroquí", "lebanese": "libanés", "turkish": "turco",
    "&": "y", "pickled": "encurtido", "crispy": "crocante", "creamy": "cremoso",
    "spicy": "picante", "sweet": "dulce", "smoky": "ahumado", "tasty": "rico",
    "easy": "fácil", "quick": "rápido", "homemade": "casero", "classic": "clásico",
    "stuffed": "relleno", "mashed potatoes": "puré de papas", "dressing": "aderezo",
    "marinade": "marinada", "marinated": "marinado", "glazed": "glaseado",
    "glaze": "glaseado", "filling": "relleno", "dough": "masa",
    "casserole": "cazuela", "skillet": "sartén", "wok": "wok",
    "one-pot": "una olla", "one pot": "una olla", "stir-fry": "salteado",
    "stir fry": "salteado", "fried rice": "arroz frito", "meatballs": "albóndigas",
    "meatloaf": "pan de carne", "kebabs": "brochettes", "teriyaki": "teriyaki",
    "ramen": "ramen", "paella": "paella", "risotto": "risotto",
    "lasagna": "lasaña", "lasagne": "lasaña", "gnocchi": "ñoquis",
    "ravioli": "ravioles", "frittata": "frittata", "omelette": "omelette",
    "quiche": "tarta", "pancakes": "panqueques", "oatmeal": "avena",
    "granola": "granola", "smoothie": "licuado", "guacamole": "guacamole",
    "hummus": "hummus", "falafel": "falafel", "tahini": "tahini", "miso": "miso",
    "polenta": "polenta", "fries": "papas fritas", "french fries": "papas fritas",
    "onion rings": "aros de cebolla", "coleslaw": "ensalada de repollo",
    "potato salad": "ensalada de papa", "caesar": "césar", "ceviche": "ceviche",
    "tartare": "tartar", "tempura": "tempura", "sushi": "sushi", "poke": "poke",
    "congee": "arroz caldoso", "naan": "pan naan", "pita": "pan pita",
    "empanada": "empanada", "arepa": "arepa", "tamal": "tamal",
    "enchilada": "enchilada", "quesadilla": "quesadilla", "fajita": "fajita",
    "nachos": "nachos", "oyster": "ostra", "oysters": "ostras",
    "scallops": "vieiras", "lobster": "langosta", "crab": "cangrejo",
    "anchovy": "anchoa", "sardine": "sardina", "trout": "trucha",
    "sea bass": "lubina", "sole": "lenguado", "rabbit": "conejo", "veal": "ternera",
    "steak": "bife", "sirloin": "lomo", "tenderloin": "lomo", "ribs": "costillas",
    "wings": "alitas", "thighs": "muslos", "thigh": "muslo", "breasts": "pechugas",
    "breast": "pechuga", "liver": "hígado", "cookies": "galletitas",
    "muffins": "muffins", "porridge": "papilla de avena",
}


def traducir_en_es(texto: str) -> str:
    """Traducción automática aproximada EN->ES por glosario (sin API key)."""
    if not texto:
        return ""
    out = f" {texto} "
    for en in sorted(EN_ES, key=len, reverse=True):
        out = re.sub(
            r"(?i)(?<![a-záéíóúñ])" + re.escape(en) + r"(?![a-záéíóúñ])",
            EN_ES[en],
            out,
        )
    out = re.sub(r"\s+", " ", out).strip()
    return out[0].upper() + out[1:] if out else out


def meal_detail(id_meal: str, timeout=7):
    """Detalle completo de una receta de TheMealDB."""
    try:
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={urllib.parse.quote_plus(str(id_meal))}"
        req = urllib.request.Request(url, headers={"User-Agent": "semana-saludable/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        meals = data.get("meals") or []
        return meals[0] if meals else None
    except Exception:
        return None


def meal_a_entrada(d, ingredientes):
    """Convierte una receta real de internet al formato del menú."""
    titulo_en = (d.get("strMeal") or "").strip()
    titulo = traducir_en_es(titulo_en) or titulo_en
    ings = []
    for i in range(1, 21):
        a = (d.get(f"strIngredient{i}") or "").strip()
        b = (d.get(f"strMeasure{i}") or "").strip()
        if a and a.lower() != "null":
            a_es = traducir_en_es(a)
            ings.append(f"{a_es} ({b})" if b else a_es)
    instr = (d.get("strInstructions") or "").replace("\r", " ").strip()
    partes = [p.strip(" .") for p in re.split(r"(?:\r?\n)+|\.\s+|\.\s*$", instr) if p.strip()]
    pasos = [traducir_en_es(p) for p in partes[:6] if len(p) > 8]
    yt = (d.get("strYoutube") or "").strip()
    fuente = f"https://www.themealdb.com/meal/{d.get('idMeal','')}"
    cat = traducir_en_es(d.get("strCategory") or "")
    area = (d.get("strArea") or "").strip()
    ings_norm = [normalizar(x) for x in ings]
    usados = []
    for ing in ingredientes:
        ni = normalizar(ing)
        if any(ni in x or x in ni for x in ings_norm):
            usados.append(ing)
    return {
        "dia": "",
        "dia_num": 0,
        "id": f"web-{d.get('idMeal','')}",
        "titulo": titulo,
        "titulo_original": titulo_en,
        "descripcion": f"Receta de internet · {cat}" + (f" · {area}" if area else ""),
        "tiempo": "—",
        "calorias": "—",
        "dificultad": "De internet",
        "tags": ["internet"] + ([cat.lower()] if cat else []),
        "origen": "internet",
        "foto": d.get("strMealThumb") or "",
        "fuente_url": fuente,
        "ingredientes_usan_tuyos": usados or ingredientes[:3],
        "ingredientes_detalle": ings,
        "pasos": pasos or ["Ver el paso a paso con video en el enlace de la receta."],
        "tip_saludable": "Versión saludable: cocina con poco aceite, suma verduras y ajusta la sal a gusto.",
        "ver_en_google": google_url(titulo_en or titulo),
        "ver_en_youtube": yt if yt else youtube_url(titulo_en or titulo),
        "nota_traduccion": True,
    }


def menu_desde_internet(ingredientes: List[str], dias: int, excluir: List[str]):
    """Arma el menú con recetas REALES de internet (TheMealDB), no de lista fija."""
    excl = set(excluir or [])
    terms = []
    for ing in ingredientes:
        en = ES_EN.get(normalizar(ing), normalizar(ing))
        if en and en not in terms:
            terms.append(en)
    candidatos, vistos = [], set()
    solo_salsas = pide_salsa(ingredientes)
    for t in terms[:4]:
        for m in buscar_themealdb(t):
            if m.get("id") and m["id"] not in vistos and f"web-{m['id']}" not in excl:
                if not solo_salsas and es_salsa(m.get("nombre", "")):
                    continue
                vistos.add(m["id"])
                candidatos.append(m)
        if len(candidatos) >= dias + 8:
            break
    random.shuffle(candidatos)
    menu = []
    for cand in candidatos:
        if len(menu) >= dias:
            break
        d = meal_detail(cand["id"])
        if not d:
            continue
        menu.append(meal_a_entrada(d, ingredientes))
    return menu


# ---------------------------------------------------------------- recetas hispanas (sitios AR/ES)
# Busca recetas reales en sitios de habla hispana (con prioridad argentina)
# y extrae cada receta desde su marcado schema.org/Recipe. Sin API key.
TIPOS_SALSA = ["salsa", "salsas", "aderezo", "aliño", "vinagreta", "mayonesa",
               "ketchup", "ketchúp", "mostaza", "chimichurri", "provenzal",
               "alioli", "dip", "paté", "pate", "hummus", "guacamole",
               "sauce", "dressing", "mayonnaise", "mustard", "gravy",
               "mojo", "pesto", "romesco", "tzatziki", "baba ganoush",
               "tapenade", "relish", "chutney", "pico de gallo", "sofrito",
               "fondo", "adobo", "escabeche"]


def es_salsa(titulo: str) -> bool:
    """Detecta si el título es una salsa/aderezo y no un plato."""
    t = normalizar(titulo or "")
    if re.search(r"\d+\s*salsas?\b", t):
        return True
    for s in TIPOS_SALSA:
        if t.startswith(s) or t.startswith("receta de " + s):
            return True
    if t in ("dip", "hummus", "guacamole", "chimichurri", "alioli",
             "pate", "paté", "mayonesa", "mostaza"):
        return True
    return False


def pide_salsa(ingredientes: List[str]) -> bool:
    """True si el usuario pidió explícitamente una salsa."""
    txt = " ".join(normalizar(i) for i in (ingredientes or []))
    return any(s in txt for s in TIPOS_SALSA)
PREF_AR = ["paulinacocina", "cookpad.com", "clarin.com", "lanacion", "elgourmet",
           "cucinare", "tn.com.ar", "telefe", "eltrecetv", "cocinaargentina",
           "recetasargentinas", "cocinerosargentinos", "infobae.com",
           "diariouno.com.ar", "mundorecetas"]
PREF_ES = ["recetasgratis", "kiwilimon", "recetasderechupete", "directoalpaladar",
           "cocinacaserayfacil", "pequerecetas", "recetinas", "bonviveur",
           "divinacocina", "gallinablanca", "nestlecocina", "superpollo"]
BLOQUEADOS = ["youtube.com", "youtu.be", "facebook.com", "instagram.com",
              "tiktok.com", "twitter.com", "pinterest.com", "amazon.",
              "mercadolibre", "duckduckgo.com"]
# URLs que son índices o listados, no una receta concreta.
MALAS_URL = ["/recetario", "/page/", "/pagina", "/category", "/tag/", "/archivo",
             "/blog", "?s=", "/search", "/autor", "/author", "/etiqueta"]

UA_BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def buscar_bing_recetas(query: str, timeout=10) -> List[str]:
    """URLs de recetas vía Bing HTML (funciona sin API key).
    Bing envuelve los links en /ck/a con la URL real en base64 (parámetro u)."""
    try:
        url = ("https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
               + "&setlang=es-AR&cc=ar&mkt=es-AR")
        req = urllib.request.Request(url, headers={"User-Agent": UA_BROWSER,
                                                   "Accept-Language": "es-AR,es;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="ignore")
        urls = []
        for bloque in html.split('<li class="b_algo"')[1:]:
            m = re.search(r'u=a1([A-Za-z0-9%_.\-~+/=]+)', bloque)
            if not m:
                continue
            raw = urllib.parse.unquote(m.group(1))
            try:
                u = base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", errors="ignore")
            except Exception:
                continue
            ul = u.lower()
            if not u.startswith("http"):
                continue
            if any(b in ul for b in BLOQUEADOS + ["bing.com", "msn.com", "microsoft.com"]):
                continue
            if u not in urls:
                urls.append(u)
        return urls
    except Exception:
        return []


def puntuar_url(url: str):
    u = url.lower()
    for i, d in enumerate(PREF_AR):
        if d in u:
            return (0, i)
    for i, d in enumerate(PREF_ES):
        if d in u:
            return (1, i)
    return (2, 99)


def buscar_recipe_ld(data):
    if isinstance(data, dict):
        t = data.get("@type")
        if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
            return data
        for v in data.values():
            if isinstance(v, (dict, list)):
                r = buscar_recipe_ld(v)
                if r:
                    return r
    elif isinstance(data, list):
        for v in data:
            if isinstance(v, (dict, list)):
                r = buscar_recipe_ld(v)
                if r:
                    return r
    return None


def normalizar_receta_ld(rec, url: str, ingredientes: List[str]):
    nombre = str(rec.get("name") or "").strip()
    ings = rec.get("recipeIngredient") or rec.get("ingredients") or []
    if isinstance(ings, str):
        ings = [ings]
    ings = [str(x).strip() for x in ings if str(x).strip()]
    instr = rec.get("recipeInstructions") or []
    if isinstance(instr, str):
        instr = [p.strip() for p in re.split(r"\n+|\.\s+", instr) if p.strip()]
    pasos = aplanar_pasos(instr)
    img = rec.get("image")
    if isinstance(img, list):
        img = img[0] if img else ""
    if isinstance(img, dict):
        img = img.get("url", "")
    if not nombre or len(ings) < 2 or not pasos:
        return None
    dominio = urllib.parse.urlparse(url).netloc.replace("www.", "")
    es_ar = puntuar_url(url)[0] == 0
    rid = "ar-" + hashlib.md5(url.encode()).hexdigest()[:12]
    ings_norm = [normalizar(x) for x in ings]
    usados = []
    for ing in ingredientes:
        ni = normalizar(ing)
        if any(ni in x or x in ni for x in ings_norm):
            usados.append(ing)
    return {
        "dia": "",
        "dia_num": 0,
        "id": rid,
        "titulo": nombre,
        "descripcion": f"Receta de {dominio}" + (" · Argentina" if es_ar else ""),
        "tiempo": str(rec.get("totalTime") or rec.get("cookTime") or "—").replace("PT", "").replace("M", " min").strip() or "—",
        "calorias": "—",
        "dificultad": "De internet",
        "tags": ["internet", "argentina" if es_ar else "español"],
        "origen": "internet",
        "foto": img if isinstance(img, str) else "",
        "fuente_url": url,
        "ingredientes_usan_tuyos": usados or ingredientes[:3],
        "ingredientes_detalle": ings,
        "pasos": pasos[:6],
        "tip_saludable": "Versión saludable: cocina con poco aceite, suma verduras y ajusta la sal a gusto.",
        "ver_en_google": google_url(nombre),
        "ver_en_youtube": youtube_url(nombre + " receta"),
    }


def aplanar_pasos(instr):
    pasos = []

    def rec(x):
        if isinstance(x, str):
            t = x.strip().strip(".")
            if len(t) > 8:
                pasos.append(t)
        elif isinstance(x, dict):
            t = str(x.get("text") or "").strip().strip(".")
            if len(t) > 8:
                pasos.append(t)
            for k in ("itemListElement", "steps", "hasPart"):
                v = x.get(k)
                if isinstance(v, list):
                    for i in v:
                        rec(i)
        elif isinstance(x, list):
            for i in x:
                rec(i)

    rec(instr)
    return pasos


def limpiar_html_txt(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = re.sub(r"&(amp|quot|lt|gt);",
               lambda m: {"amp": "&", "quot": '"', "lt": "<", "gt": ">"}[m.group(1)], s)
    return re.sub(r"\s+", " ", s).strip()


def armar_entrada_web(titulo, ings, pasos, foto, url, ingredientes):
    dominio = urllib.parse.urlparse(url).netloc.replace("www.", "")
    es_ar = puntuar_url(url)[0] == 0
    rid = "ar-" + hashlib.md5(url.encode()).hexdigest()[:12]
    ings_norm = [normalizar(x) for x in ings]
    usados = []
    for ing in ingredientes:
        ni = normalizar(ing)
        if any(ni in x or x in ni for x in ings_norm):
            usados.append(ing)
    return {
        "dia": "",
        "dia_num": 0,
        "id": rid,
        "titulo": titulo,
        "descripcion": f"Receta de {dominio}" + (" · Argentina" if es_ar else ""),
        "tiempo": "—",
        "calorias": "—",
        "dificultad": "De internet",
        "tags": ["internet", "argentina" if es_ar else "español"],
        "origen": "internet",
        "foto": foto if isinstance(foto, str) else "",
        "fuente_url": url,
        "ingredientes_usan_tuyos": usados or ingredientes[:3],
        "ingredientes_detalle": ings,
        "pasos": pasos[:6],
        "tip_saludable": "Versión saludable: cocina con poco aceite, suma verduras y ajusta la sal a gusto.",
        "ver_en_google": google_url(titulo),
        "ver_en_youtube": youtube_url(titulo + " receta"),
    }


def extraer_receta_html(url: str, ingredientes: List[str], timeout=7):
    """Fallback: extrae ingredientes/pasos desde el HTML (listas tras encabezados)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA_BROWSER,
                                                    "Accept-Language": "es-AR,es;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if "html" not in (r.headers.get("Content-Type", "")):
                return None
            html = r.read(600000).decode("utf-8", errors="ignore")

        def lista_tras(patron, min_len=1):
            m = re.search(patron, html, re.I | re.S)
            if not m:
                return []
            seg = html[m.end(): m.end() + 8000]
            mh = re.search(r"<h[1-4][^>]*>", seg, re.I)
            zonas = [seg[: mh.start()]] if mh else []
            zonas.append(seg)

            def buscar_lista(zona):
                lm = re.search(r"<(ul|ol)[^>]*>(.*?)</\1>", zona, re.S | re.I)
                if lm:
                    return [limpiar_html_txt(x) for x in
                            re.findall(r"<li[^>]*>(.*?)</li>", lm.group(2), re.S | re.I)]
                return []

            items = []
            for zona in zonas:
                items = [x for x in buscar_lista(zona) if x]
                if len(items) >= 3:
                    break
            if len(items) < 3:
                # fallback: párrafos sueltos (algunos sitios no usan listas)
                zona = zonas[0]
                ps = [limpiar_html_txt(x) for x in
                      re.findall(r"<p[^>]*>(.*?)</p>", zona, re.S | re.I)]
                ps = [x for x in ps if x]
                fus = []
                k = 0
                while k < len(ps):
                    if re.match(r"(?i)^paso\s*\d+", ps[k]) and k + 1 < len(ps):
                        fus.append(ps[k] + ": " + ps[k + 1])
                        k += 2
                    else:
                        fus.append(ps[k])
                        k += 1
                items = fus
            return [x for x in items if len(x) >= min_len]

        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
        titulo = limpiar_html_txt(h1.group(1)) if h1 else ""
        if len(titulo) > 120:
            titulo = titulo[:120]
        og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
                       html, re.I)
        foto = og.group(1) if og else ""
        ings = lista_tras(r"<h[1-4][^>]*>.*?ingredientes.*?</h[1-4]>", 2)[:20]
        pasos = lista_tras(
            r"<h[1-4][^>]*>.*?(preparaci[oó]n|elaboraci[oó]n|paso a paso|instrucciones|procedimiento).*?</h[1-4]>",
            20)[:8]
        if not titulo or len(ings) < 3 or not pasos:
            return None
        return armar_entrada_web(titulo, ings, pasos, foto, url, ingredientes)
    except Exception:
        return None


def extraer_receta_ld(url: str, ingredientes: List[str], timeout=7):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA_BROWSER,
                                                    "Accept-Language": "es-AR,es;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if "html" not in (r.headers.get("Content-Type", "")):
                return None
            html = r.read(600000).decode("utf-8", errors="ignore")
        for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                             html, re.S | re.I):
            try:
                data = json.loads(m.group(1).strip())
            except Exception:
                continue
            rec = buscar_recipe_ld(data)
            if rec:
                norm = normalizar_receta_ld(rec, url, ingredientes)
                if norm:
                    return norm
        return extraer_receta_html(url, ingredientes, timeout=timeout)
    except Exception:
        return None


def buscar_wp_paulina(ingredientes: List[str], timeout=10) -> List[str]:
    """Recetas de Paulina Cocina vía su API de WordPress (fuente argentina directa)."""
    try:
        q = urllib.parse.quote_plus(" ".join(ingredientes[:2]))
        url = f"https://www.paulinacocina.net/wp-json/wp/v2/search?search={q}&per_page=12"
        req = urllib.request.Request(url, headers={"User-Agent": "semana-saludable/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        urls = []
        for x in data if isinstance(data, list) else []:
            u = x.get("url") or ""
            if u.startswith("http") and u not in urls:
                urls.append(u)
        return urls
    except Exception:
        return []


def menu_desde_hispano(ingredientes: List[str], dias: int, excluir: List[str]):
    """Arma el menú con recetas REALES de sitios hispanos (prioridad AR)."""
    excl = set(excluir or [])
    base = ingredientes[:3]
    urls = [u for u in buscar_wp_paulina(base) if u not in excl]
    queries = []
    if len(base) >= 2:
        queries.append(f"receta {base[0]} {base[1]} fácil argentina")
        queries.append(f"{base[0]} con {base[1]} receta paso a paso")
    if base:
        queries.append(f"recetas con {base[0]} cocina argentina")
    # búsquedas directas dentro de los mejores sitios (traen la receta, no la portada)
    for d in ["paulinacocina.net", "cookpad.com/ar", "recetasgratis.net"]:
        queries.append(f"site:{d} {' '.join(base[:2])}")
    if base:
        queries.append(f"receta de {base[0]} fácil")
    for q in queries[:7]:
        for u in buscar_bing_recetas(q):
            ul = u.lower()
            if any(m in ul for m in MALAS_URL):
                continue
            path = urllib.parse.urlparse(u).path.rstrip("/").lower()
            if path in ("", "/recetas", "/receta", "/recipes", "/ar"):
                continue
            if u not in urls and u not in excl:
                urls.append(u)
        if len(urls) >= dias + 12:
            break
    urls.sort(key=puntuar_url)
    urls = urls[: dias + 10]
    resultados = []
    vistos_titulos = set()
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    try:
        futs = [ex.submit(extraer_receta_ld, u, ingredientes) for u in urls]
        for fut in concurrent.futures.as_completed(futs, timeout=30):
            try:
                r = fut.result()
            except Exception:
                r = None
            if not r:
                continue
            # descarta páginas-índice ("57 recetas fáciles...") y duplicados
            if re.search(r"\d+\s*recetas|recetario", r["titulo"] or "", re.I):
                continue
            # obvia salsas salvo pedido explícito (platos, no aderezos)
            if not pide_salsa(ingredientes) and es_salsa(r["titulo"]):
                continue
            nt = normalizar(r["titulo"])
            if r["id"] in {x["id"] for x in resultados} or nt in vistos_titulos:
                continue
            vistos_titulos.add(nt)
            resultados.append(r)
            if len(resultados) >= dias:
                break
    except Exception:
        pass
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    return resultados[:dias]


# ---------------------------------------------------------------- modelos

class GenerateIn(BaseModel):
    ingredientes: object = Field(default_factory=list)  # lista o string
    dias: int = Field(default=7, ge=1, le=7)
    preferencias: List[str] = Field(default_factory=list)
    dias_nombres: Optional[List[str]] = None  # ej: ["Lunes","Miércoles"]
    excluir: List[str] = Field(default_factory=list)  # ids de recetas a evitar (variedad)
    fuente: str = Field(default="auto")  # auto | argentina | internet | curadas


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
    prefs = body.preferencias or []

    # Días: si el frontend envía nombres seleccionados (globos), se respetan tal cual.
    nombres = []
    if body.dias_nombres:
        elegidos = {normalizar(x) for x in body.dias_nombres}
        nombres = [d for d in DIAS if normalizar(d) in elegidos]
    if nombres:
        dias = len(nombres)
    else:
        dias = max(1, min(7, int(body.dias or 7)))
        nombres = DIAS[:dias]
    ing_norm = [normalizar(i) for i in ingredientes]

    candidatas = [r for r in RECETAS if cumple_preferencias(r, prefs)] or list(RECETAS)

    # Variedad: evita recetas ya mostradas y agrega azar al ranking
    # para que cada generación traiga opciones distintas y creativas.
    excluidos = set(body.excluir or [])
    pool_base = [r for r in candidatas if r["id"] not in excluidos]
    if len(pool_base) < dias:
        pool_base = list(candidatas)
    rankeadas = sorted(
        pool_base,
        key=lambda r: score_receta(r, ing_norm) + random.uniform(0, 3.0),
        reverse=True,
    )

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

    # enriquecer cada día (menú curado)
    semana_curada = []
    for i, rec in enumerate(menu):
        usados = []
        for b in rec["ingredientes_base"]:
            nb = normalizar(b)
            if any((ing in nb or nb in ing) for ing in ing_norm):
                usados.append(b)
        semana_curada.append(
            {
                "dia": nombres[i],
                "dia_num": i + 1,
                "id": rec["id"],
                "titulo": rec["titulo"],
                "descripcion": rec["descripcion"],
                "tiempo": rec["tiempo"],
                "calorias": rec["calorias"],
                "dificultad": rec["dificultad"],
                "tags": rec["tags"],
                "origen": "curada",
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

    # menú con recetas REALES de internet (no lista fija); con fallback a curadas
    # auto = sitios argentinos primero, luego mundo, luego curadas
    modo = (body.fuente or "auto").lower()
    semana = semana_curada
    fuente_usada = "curadas"
    if modo in ("auto", "argentina"):
        ar = []
        try:
            ar = menu_desde_hispano(ingredientes, dias, body.excluir or [])
        except Exception:
            ar = []
        if len(ar) >= dias:
            semana = ar[:dias]
            fuente_usada = "argentina"
        elif ar and modo == "argentina":
            ids_ar = {w["id"] for w in ar}
            faltan = [e for e in semana_curada if e["id"] not in ids_ar][: dias - len(ar)]
            semana = ar + faltan
            fuente_usada = "mixta"
    if fuente_usada == "curadas" and modo in ("auto", "internet"):
        web = []
        try:
            web = menu_desde_internet(ingredientes, dias, body.excluir or [])
        except Exception:
            web = []
        if len(web) >= dias:
            semana = web[:dias]
            fuente_usada = "internet"
        elif web and modo == "internet":
            ids_web = {w["id"] for w in web}
            faltan = [e for e in semana_curada if e["id"] not in ids_web][: dias - len(web)]
            semana = web + faltan
            fuente_usada = "mixta"
    for i, entry in enumerate(semana):
        entry["dia"] = nombres[i]
        entry["dia_num"] = i + 1

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
        "fuente_usada": fuente_usada,
        "menu": semana,
        "lista_compras": lista_compras,
        "inspiracion_internet": inspiracion,
        "nota": "Tus ingredientes son la base, no el límite: cada receta suma más alimentos para que sea completa y saludable.",
    }


# Para `vercel dev` / uvicorn local
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)
