"""
usda_api.py

Este archivo conecta con la API de USDA FoodData Central para buscar
alimentos reales y traer sus datos nutricionales. NO decide qué se
prohíbe -- eso lo sigue haciendo filtros_seguridad.py. Este archivo solo
se encarga de:
    1. Buscar alimentos en la API de USDA
    2. Convertirlos al mismo formato que ya usa filtrar_alimentos():
       {"nombre": ..., "etiquetas": {...}}

Cómo infiere las etiquetas (punto de partida, se ajusta con el tiempo):
    - Nutrientes: si el sodio/azúcar/potasio/fósforo superan un umbral,
      se agrega la etiqueta correspondiente (alto_sodio, alto_azucar, etc).
    - Texto: si la descripción o lista de ingredientes contiene palabras
      clave (leche, trigo, cacahuate, camarón, huevo, soya...), se agrega
      la etiqueta de alergeno correspondiente.

Esto NO es perfecto: la API de USDA no viene con etiquetas de alergenos
ya hechas, así que estas reglas son una primera aproximación razonable.
Hay que revisarlas con alimentos reales y ajustar umbrales/palabras.

Requiere: pip install requests python-dotenv

Cómo correrlo (modo de prueba, con una búsqueda real a la API):
    python3 src/usda_api.py
"""

import os
import re
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.environ.get("USDA_API_KEY")
URL_BASE = "https://api.nal.usda.gov/fdc/v1"

UMBRAL_SODIO_MG = 400
UMBRAL_AZUCAR_G = 15
UMBRAL_POTASIO_MG = 400
UMBRAL_FOSFORO_MG = 300

PALABRAS_ETIQUETA = {
    "lactosa": ["milk", "leche", "dairy", "lactose", "cheese", "queso",
                "yogurt", "cream", "crema", "butter", "mantequilla",
                "buttermilk", "milkfat", "milk solids", "whey", "casein"],
    "gluten": ["wheat", "trigo", "gluten", "barley", "cebada", "rye",
               "centeno", "malt extract", "malted", "barley malt",
               "malta"],
    "frutos_secos": ["peanut", "cacahuate", "almond", "almendra", "walnut",
                      "nuez", "cashew", "pistachio", "pistache",
                      "hazelnut", "avellana", "pecan"],
    "mariscos": ["shrimp", "camaron", "camarón", "crab", "cangrejo",
                 "lobster", "langosta", "shellfish", "clam", "almeja",
                 "oyster", "ostion", "mussel", "mejillon", "fish", "pescado"],
    "huevo": ["egg", "huevo"],
    "soya": ["soy", "soya", "soja", "soybean", "soybeans", "soyabean",
             "soymilk"],
}


def buscar_alimentos(query, page_size=10, api_key=None):
    """
    Busca alimentos en la API de USDA por nombre (ej. "chicken breast").
    Devuelve la lista cruda de resultados, tal como la manda la API.
    """
    api_key = api_key or API_KEY
    if not api_key:
        raise ValueError(
            "No se encontró USDA_API_KEY. Revisa que tu archivo .env "
            "tenga la línea USDA_API_KEY=tu_key_aqui"
        )

    respuesta = requests.get(
        f"{URL_BASE}/foods/search",
        params={"api_key": api_key, "query": query, "pageSize": page_size},
        timeout=10,
    )
    respuesta.raise_for_status()
    return respuesta.json().get("foods", [])


def _extraer_nutriente(alimento_json, nombres_buscados):
    """
    Busca en la lista foodNutrients del alimento el primer nutriente cuyo
    nombre contenga alguna de las palabras en 'nombres_buscados'
    (sin importar mayúsculas/minúsculas). Devuelve su valor numérico,
    o None si no se encontró.
    """
    for nutriente in alimento_json.get("foodNutrients", []):
        nombre = (nutriente.get("nutrientName") or "").lower()
        if any(n.lower() in nombre for n in nombres_buscados):
            return nutriente.get("value")
    return None


def inferir_etiquetas(alimento_json):
    """
    A partir de un alimento tal como lo devuelve la API de USDA,
    infiere un set de etiquetas usando reglas simples de nutrientes
    y de texto (nombre + ingredientes).
    """
    etiquetas = set()

    sodio = _extraer_nutriente(alimento_json, ["sodium"])
    if sodio is not None and sodio >= UMBRAL_SODIO_MG:
        etiquetas.add("alto_sodio")

    azucar = _extraer_nutriente(alimento_json, ["sugars, total", "total sugars", "sugars"])
    if azucar is not None and azucar >= UMBRAL_AZUCAR_G:
        etiquetas.add("alto_azucar")

    potasio = _extraer_nutriente(alimento_json, ["potassium"])
    if potasio is not None and potasio >= UMBRAL_POTASIO_MG:
        etiquetas.add("alto_potasio")

    fosforo = _extraer_nutriente(alimento_json, ["phosphorus"])
    if fosforo is not None and fosforo >= UMBRAL_FOSFORO_MG:
        etiquetas.add("alto_fosforo")

    texto = " ".join([
        alimento_json.get("description", "") or "",
        alimento_json.get("ingredients", "") or "",
    ]).lower()

    for etiqueta, palabras in PALABRAS_ETIQUETA.items():
        # \b...\b exige que la palabra clave aparezca COMPLETA (con límites
        # de palabra a los lados), no como parte de otra palabra más larga.
        # Esto evita falsos positivos como "malt" haciendo match dentro de
        # "maltodextrin" (que normalmente no contiene gluten).
        if any(re.search(r"\b" + re.escape(palabra) + r"\b", texto) for palabra in palabras):
            etiquetas.add(etiqueta)

    return etiquetas


def usda_a_formato_interno(alimento_json):
    return {
        "nombre": alimento_json.get("description", "Alimento sin nombre"),
        "fdc_id": alimento_json.get("fdcId"),
        "etiquetas": inferir_etiquetas(alimento_json),
        "info_nutricional": {
            "calorias": _extraer_nutriente(alimento_json, ["energy"]),
            "sodio_mg": _extraer_nutriente(alimento_json, ["sodium"]),
            "azucar_g": _extraer_nutriente(alimento_json, ["sugars, total", "total sugars", "sugars"]),
            "proteina_g": _extraer_nutriente(alimento_json, ["protein"]),
            "carbohidratos_g": _extraer_nutriente(
                alimento_json, ["carbohydrate, by difference"]),
            "grasas_g": _extraer_nutriente(alimento_json, ["total lipid (fat)"]),
        },
    }


def buscar_y_convertir(query, page_size=10, api_key=None):
    """
    Busca alimentos en USDA y los devuelve ya convertidos al formato
    interno, listos para pasarle directo a filtrar_alimentos().
    """
    resultados = buscar_alimentos(query, page_size=page_size, api_key=api_key)
    return [usda_a_formato_interno(a) for a in resultados]


if __name__ == "__main__":
    alimentos = buscar_y_convertir("milk", page_size=5)

    print("=== Resultados de USDA para 'milk' ===\n")
    for a in alimentos:
        print(a["nombre"])
        print(f"  etiquetas inferidas: {sorted(a['etiquetas']) if a['etiquetas'] else 'ninguna'}")
        print(f"  nutrientes: {a['info_nutricional']}")
        print()