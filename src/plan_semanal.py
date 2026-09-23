"""
plan_semanal.py

Conecta TODO lo que ya existe en src/ en un solo flujo. No modifica ni
reemplaza ningún archivo — solo los importa y los usa en orden:

    1. predict.py            -> predice calorías/macros del día (la red)
    2. filtros_seguridad.py  -> calcula qué etiquetas hay que evitar
                                 (enfermedades/alergias del usuario)
    3. usda_api.py           -> busca alimentos reales en USDA y les
                                 aplica el filtro de seguridad
    4. horarios.py           -> reparte el total del día en comidas,
                                 a qué hora, por cada día de la semana

Cómo correrlo (ejemplo al final del archivo):
    python3 src/plan_semanal.py
"""

import numpy as np

try:
    from scipy.optimize import nnls
except ImportError:
    nnls = None

from predict import predecir_usuario
from filtros_seguridad import etiquetas_prohibidas, filtrar_alimentos
from usda_api import buscar_y_convertir
from horarios import armar_plan_dia

NOMBRES_MACROS = ["calorias_diarias", "proteina_g", "carbohidratos_g", "grasas_g"]


# Categorías base de búsqueda en USDA, para armar un catálogo de
# alimentos reales ya filtrado por seguridad. Ajusta/agrega términos
# según lo que quieras poder sugerir.
BUSQUEDAS_POR_CATEGORIA = {
    "proteina": ["chicken breast", "salmon", "eggs", "tofu", "lean beef"],
    "carbohidrato": ["rice", "oats", "potato", "whole wheat bread", "quinoa"],
    "grasa": ["avocado", "olive oil", "almonds", "peanut butter"],
    "vegetal": ["broccoli", "spinach", "carrot", "mixed vegetables"],
}

# Nombre "bonito" en español para cada término de búsqueda. USDA no
# tiene descripciones en español, así que en vez de traducir texto libre
# (poco confiable) le ponemos nosotros un nombre limpio a cada búsqueda
# que ya conocemos de antemano.
NOMBRE_ES_POR_QUERY = {
    "chicken breast": "Pechuga de pollo",
    "salmon": "Salmón",
    "eggs": "Huevo",
    "tofu": "Tofu",
    "lean beef": "Res magra",
    "rice": "Arroz",
    "oats": "Avena",
    "potato": "Papa",
    "whole wheat bread": "Pan integral",
    "quinoa": "Quinoa",
    "avocado": "Aguacate",
    "olive oil": "Aceite de oliva",
    "almonds": "Almendras",
    "peanut butter": "Crema de cacahuate",
    "broccoli": "Brócoli",
    "spinach": "Espinaca",
    "carrot": "Zanahoria",
    "mixed vegetables": "Verduras mixtas",
}

CATEGORIA_ES = {
    "proteina": "Proteína",
    "carbohidrato": "Carbohidrato",
    "grasa": "Grasa",
    "vegetal": "Vegetal",
}


def obtener_catalogo_alimentos(etiquetas_a_evitar, page_size=5):
    """
    Busca en USDA un catálogo base de alimentos por categoría y le
    aplica el filtro de seguridad (filtros_seguridad.filtrar_alimentos).

    Devuelve: dict {"proteina": [alimentos permitidos...], "carbohidrato": [...], ...}
    """
    catalogo = {}
    for categoria, queries in BUSQUEDAS_POR_CATEGORIA.items():
        alimentos_categoria = []
        for query in queries:
            try:
                encontrados = buscar_y_convertir(query, page_size=page_size)
            except Exception as error:
                print(f"  Aviso: no se pudo buscar '{query}' en USDA ({error})")
                continue
            # Le pegamos el nombre en español (según el término de búsqueda)
            # y guardamos el original de USDA por si se necesita para debug.
            for alimento in encontrados:
                alimento["nombre_usda"] = alimento["nombre"]
                alimento["nombre"] = NOMBRE_ES_POR_QUERY.get(query, alimento["nombre"])
            alimentos_categoria.extend(encontrados)

        permitidos, excluidos = filtrar_alimentos(alimentos_categoria, etiquetas_a_evitar)
        catalogo[categoria] = permitidos

        if excluidos:
            print(f"  '{categoria}': se excluyeron {len(excluidos)} alimentos por seguridad")

    return catalogo


def _vector_nutrientes_por_gramo(alimento):
    """
    Devuelve [calorias, proteina_g, carbohidratos_g, grasas_g] POR GRAMO
    para un alimento (los datos de USDA vienen por 100g, así que se
    divide entre 100). Devuelve None si al alimento le falta algún
    nutriente (no se puede usar para armar combinaciones).
    """
    info = alimento.get("info_nutricional", {})
    valores = [
        info.get("calorias"),
        info.get("proteina_g"),
        info.get("carbohidratos_g"),
        info.get("grasas_g"),
    ]
    if any(v is None for v in valores):
        return None
    return [v / 100.0 for v in valores]


def armar_alimentos_comida(macros_comida, catalogo, gramos_minimos=5, max_alimentos=6):
    """
    Dado el objetivo de macros de UNA comida y el catálogo de alimentos
    permitidos (ya pasaron el filtro de seguridad), elige una
    COMBINACIÓN LIBRE de alimentos -- no un alimento fijo por categoría --
    que se acerque lo más posible a ese objetivo.

    Cómo funciona: arma un sistema de ecuaciones (4 nutrientes objetivo x
    N alimentos posibles) y lo resuelve con mínimos cuadrados no-negativos
    (NNLS): "¿cuántos gramos de cada alimento hacen falta para acercarse
    al objetivo, sin que ningún alimento tenga gramos negativos?". NNLS
    tiende a dar soluciones dispersas (pocos alimentos con gramos > 0),
    así que no hace falta forzar una categoría por comida -- el propio
    algoritmo decide qué combinar.

    Requiere scipy (pip install scipy; ya viene como dependencia de
    scikit-learn, pero agrégalo a requirements.txt de todas formas).

    Devuelve:
        alimentos_elegidos: [{"nombre":, "categoria":, "gramos":}, ...]
        macros_logrados: dict con los 4 macros que SÍ da esa combinación
                         (para comparar contra el objetivo real)
    """
    if nnls is None:
        raise ImportError(
            "armar_alimentos_comida necesita scipy. Instálalo con: pip install scipy"
        )

    # Aplanar el catálogo (categoria -> lista de alimentos) en una sola
    # lista, sin perder de qué categoría venía cada uno.
    pool = []
    for categoria, alimentos in catalogo.items():
        for alimento in alimentos:
            vector = _vector_nutrientes_por_gramo(alimento)
            if vector is None:
                continue  # a este alimento le falta proteina/carbos/grasas en USDA
            pool.append((alimento, categoria, vector))

    if not pool:
        return [], {nombre: 0.0 for nombre in NOMBRES_MACROS}

    # A: 4 filas (calorias, proteina, carbohidratos, grasas) x N alimentos
    A = np.array([vector for _, _, vector in pool]).T
    b = np.array([macros_comida[nombre] for nombre in NOMBRES_MACROS])

    gramos, _residual = nnls(A, b)

    # Descartar lo que NNLS dejó en (casi) cero
    candidatos = [
        (alimento, categoria, g)
        for (alimento, categoria, _), g in zip(pool, gramos)
        if g >= gramos_minimos
    ]
    # Si aun así quedan muchos alimentos con aportes chicos, nos quedamos
    # con los de mayor peso para que la comida sea realista de preparar
    candidatos.sort(key=lambda tupla: tupla[2], reverse=True)
    candidatos = candidatos[:max_alimentos]

    alimentos_elegidos = []
    macros_logrados = {nombre: 0.0 for nombre in NOMBRES_MACROS}
    for alimento, categoria, g in candidatos:
        vector = _vector_nutrientes_por_gramo(alimento)
        for nombre, valor_por_gramo in zip(NOMBRES_MACROS, vector):
            macros_logrados[nombre] += valor_por_gramo * g
        alimentos_elegidos.append({
            "nombre": alimento["nombre"],
            "categoria": categoria,
            "gramos": round(float(g), 1),
        })

    macros_logrados = {k: round(v, 1) for k, v in macros_logrados.items()}
    return alimentos_elegidos, macros_logrados


def generar_plan_semana(
    edad, sexo, altura_cm, peso_kg, nivel_actividad, objetivo,
    enfermedades, alergias,
    hora_despertar, hora_dormir, num_comidas,
    actividades_por_dia, descansos_por_dia=None,
    incluir_catalogo_usda=True,
    asignar_alimentos=True,
):
    """
    Arma el plan semanal completo.

    actividades_por_dia: dict, ej.
        {
            "lunes": [{"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"}],
            "martes": [...],
            ...
        }
    descansos_por_dia: opcional, mismo formato que actividades_por_dia.

    Devuelve un dict con:
        resultado_red       -> lo que predijo la red (fijo toda la semana)
        avisos_seguridad    -> enfermedades/alergias que necesitan revisión manual
        catalogo_alimentos  -> alimentos reales de USDA ya filtrados por seguridad
        plan_semana         -> dict {dia: [comidas con hora y macros]}
    """
    # --- 1. Predicción de la red (una sola vez: es el mismo total toda la semana) ---
    resultado_red = predecir_usuario(
        edad=edad, sexo=sexo, altura_cm=altura_cm, peso_kg=peso_kg,
        nivel_actividad=nivel_actividad, objetivo=objetivo,
    )

    # --- 2. Filtros de seguridad ---
    etiquetas_evitar, avisos = etiquetas_prohibidas(enfermedades, alergias)

    # --- 3. Catálogo de alimentos reales ya filtrado (opcional, tarda por la API) ---
    catalogo = {}
    if incluir_catalogo_usda:
        catalogo = obtener_catalogo_alimentos(etiquetas_evitar)

    # --- 4. Horario de comidas por cada día de la semana ---
    descansos_por_dia = descansos_por_dia or {}
    plan_semana = {}
    for dia, actividades in actividades_por_dia.items():
        descansos = descansos_por_dia.get(dia)
        comidas_dia = armar_plan_dia(
            resultado_red=resultado_red,
            hora_despertar=hora_despertar,
            hora_dormir=hora_dormir,
            actividades=actividades,
            num_comidas=num_comidas,
            descansos=descansos,
        )

        # --- 5. Asignar alimentos reales y gramos a cada comida ---
        # (combinación libre vía NNLS, no un alimento fijo por categoría)
        if asignar_alimentos and catalogo:
            for comida in comidas_dia:
                macros_objetivo = {nombre: comida[nombre] for nombre in NOMBRES_MACROS}
                alimentos, logrados = armar_alimentos_comida(macros_objetivo, catalogo)
                comida["alimentos"] = alimentos
                comida["macros_logrados"] = logrados

        plan_semana[dia] = comidas_dia

    return {
        "resultado_red": resultado_red,
        "avisos_seguridad": avisos,
        "catalogo_alimentos": catalogo,
        "plan_semana": plan_semana,
    }


if __name__ == "__main__":
    actividades_semana = {
        "lunes": [{"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"}],
        "martes": [{"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"},
                   {"nombre": "deporte", "inicio": "18:30", "fin": "19:30"}],
        "miercoles": [{"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"}],
    }

    plan = generar_plan_semana(
        edad=25, sexo="mujer", altura_cm=165, peso_kg=60,
        nivel_actividad="moderado", objetivo="bajar",
        enfermedades=["diabetes"], alergias=["lacteos"],
        hora_despertar="07:00", hora_dormir="23:00", num_comidas=4,
        actividades_por_dia=actividades_semana,
        incluir_catalogo_usda=True,  # pon False para probar rápido sin llamar a la API
    )

    print("=== Predicción de la red (fija toda la semana) ===")
    print(plan["resultado_red"])

    if plan["avisos_seguridad"]:
        print("\n=== Avisos de seguridad (revisión manual) ===")
        for aviso in plan["avisos_seguridad"]:
            print(f"  - {aviso}")

    print("\n=== Catálogo de alimentos permitidos (por categoría) ===")
    for categoria, alimentos in plan["catalogo_alimentos"].items():
        print(f"  {CATEGORIA_ES.get(categoria, categoria)}: {len(alimentos)} alimentos permitidos")

    nombres_comida_bonitos = {
        "desayuno": "Desayuno", "comida": "Comida", "cena": "Cena",
        "snack": "Snack", "snack_manana": "Snack (mañana)", "snack_tarde": "Snack (tarde)",
    }

    print("\n=== Plan semanal ===")
    for dia, comidas in plan["plan_semana"].items():
        print(f"\n{dia.capitalize()}")
        print("-" * 40)
        for comida in comidas:
            nombre_comida = nombres_comida_bonitos.get(comida["comida"], comida["comida"].capitalize())
            print(f"  {comida['hora']}  {nombre_comida:<16} "
                  f"objetivo: {comida['calorias_diarias']:.0f} kcal")

            for alimento in comida.get("alimentos", []):
                categoria_es = CATEGORIA_ES.get(alimento["categoria"], alimento["categoria"])
                print(f"      • {alimento['nombre']:<20} {alimento['gramos']:>6.1f} g   ({categoria_es})")

            logrado = comida.get("macros_logrados")
            if logrado:
                print(
                    f"      → logrado: {float(logrado['calorias_diarias']):.0f} kcal | "
                    f"P {float(logrado['proteina_g']):.1f}g | "
                    f"C {float(logrado['carbohidratos_g']):.1f}g | "
                    f"G {float(logrado['grasas_g']):.1f}g"
                )