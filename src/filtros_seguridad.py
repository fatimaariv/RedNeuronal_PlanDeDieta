"""
filtros_seguridad.py

Este archivo NO es parte de la red neuronal ni de la lógica de horarios.
Su trabajo es UNA cosa: dada una lista de enfermedades y alergias que
marcó el usuario, decidir qué alimentos NO se le pueden sugerir.

Todavía no usa la API de USDA (eso es el paso 4). Por ahora trabaja con
una lista de alimentos de EJEMPLO, para poder probar y afinar la lógica
de filtrado de forma aislada. Cuando se conecte USDA, lo único que va a
cambiar es DE DÓNDE sale la lista de alimentos -- el filtro en sí no se
toca, porque ya funciona sobre cualquier alimento que tenga "etiquetas".

Cómo funciona (en una frase):
    enfermedades/alergias -> etiquetas prohibidas -> se quita cualquier
    alimento que tenga alguna de esas etiquetas.

IMPORTANTE: esto NO es consejo médico. Es un mapeo inicial razonable
para un proyecto escolar/MVP. Antes de usarse con personas reales,
un profesional de nutrición debería revisar y ajustar estas tablas.

Cómo correrlo (modo de prueba, con datos de ejemplo):
    python3 src/filtros_seguridad.py
"""

import re
import unicodedata


def normalizar_texto(texto):
    """Minúsculas y sin acentos, para comparar 'Salmón' con 'salmon'."""
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def contiene_palabra(texto, palabra):
    """
    True si 'palabra' aparece COMPLETA en 'texto' (también en plural:
    almendra/almendras, egg/eggs, nuez/nueces). Ignora mayúsculas y acentos.
    Evita falsos positivos por subcadenas: 'pa' ya no coincide con 'Papa'.
    """
    texto = normalizar_texto(texto)
    palabra = normalizar_texto(palabra).strip()
    if not palabra:
        return False
    if palabra.endswith("z"):
        # nuez -> nueces, maiz -> maices
        patron = r"\b(?:" + re.escape(palabra) + "|" + re.escape(palabra[:-1] + "ces") + r")\b"
    else:
        patron = r"\b" + re.escape(palabra) + r"(?:s|es)?\b"
    return re.search(patron, texto) is not None


# --- Alergias: mapeo directo, 1 a 1 ---
# Si el usuario marca esta alergia, se prohíbe esta etiqueta exacta.
ALERGIAS_A_ETIQUETAS = {
    "lacteos": {"lactosa"},
    "gluten": {"gluten"},
    "frutos_secos": {"frutos_secos"},
    "mariscos": {"mariscos"},
    "huevo": {"huevo"},
    "soya": {"soya"},
    "ninguna": set(),
    # "otra" se maneja aparte (no se puede auto-filtrar, ver abajo)
}

# --- Enfermedades: qué CATEGORÍAS de alimento conviene evitar ---
# Esto es más impreciso que las alergias (no es "contiene X o no"),
# así que son categorías de riesgo conocidas, no una lista exhaustiva.
ENFERMEDADES_A_ETIQUETAS = {
    "diabetes": {"alto_azucar"},
    "hipertension": {"alto_sodio"},
    "enfermedad_renal": {"alto_sodio", "alto_potasio", "alto_fosforo"},
    # Hipotiroidismo NO tiene una restricción absoluta y clara como las
    # de arriba (el tema de los alimentos bociogénicos es más matizado
    # y depende de cada caso) -> no se autofiltra nada, pero se avisa.
    "hipotiroidismo": set(),
    "ninguna": set(),
    # "otra" se maneja aparte (no se puede auto-filtrar, ver abajo)
}

# Condiciones que existen en la tabla pero donde CONSCIENTEMENTE no se
# quita ningún alimento automáticamente, porque la relación alimento-riesgo
# no es tan directa como en diabetes/hipertensión. Se usan para generar
# una alerta de revisión manual, no para fallar en silencio.
CONDICIONES_SIN_AUTOFILTRO = {"hipotiroidismo"}


def etiquetas_prohibidas(enfermedades=None, alergias=None):
    """
    Junta las enfermedades y alergias del usuario y devuelve:
      - un set con todas las etiquetas que hay que evitar
      - una lista de avisos para revisión manual (casos donde el sistema
        NO pudo generar una regla de filtrado automática)

    enfermedades, alergias: listas de strings, ej.
        enfermedades=["diabetes", "hipertension"]
        alergias=["lacteos", "otra"]
    """
    enfermedades = enfermedades or []
    alergias = alergias or []

    prohibidas = set()
    avisos = []

    for enfermedad in enfermedades:
        clave = enfermedad.strip().lower()
        if clave == "otra":
            avisos.append(
                "Se marcó una enfermedad 'Otra' sin especificar: "
                "no se puede generar un filtro automático. Requiere revisión manual."
            )
            continue
        if clave not in ENFERMEDADES_A_ETIQUETAS:
            avisos.append(f"Enfermedad no reconocida: '{enfermedad}'. Revisar manualmente.")
            continue
        if clave in CONDICIONES_SIN_AUTOFILTRO:
            avisos.append(
                f"'{enfermedad}' no tiene un filtro automático definido "
                "(la relación alimento-riesgo no es directa). Revisar manualmente."
            )
        prohibidas |= ENFERMEDADES_A_ETIQUETAS[clave]

    for alergia in alergias:
        clave = alergia.strip().lower()
        if clave == "otra":
            avisos.append(
                "Se marcó una alergia 'Otra' sin especificar: "
                "no se puede generar un filtro automático. Requiere revisión manual."
            )
            continue
        if clave not in ALERGIAS_A_ETIQUETAS:
            # Alergia escrita por el usuario en "Otra alergia": se filtra
            # buscando la palabra en el nombre e ingredientes de cada alimento.
            prohibidas.add(f"custom:{clave}")
            avisos.append(
                f"Alergia personalizada '{alergia.strip()}': solo se excluyen los alimentos "
                "cuyo nombre o ingredientes la mencionan. Revisa manualmente el plan."
            )
            continue
        prohibidas |= ALERGIAS_A_ETIQUETAS[clave]

    return prohibidas, avisos


def filtrar_alimentos(lista_alimentos, etiquetas_a_evitar):
    """
    Quita de 'lista_alimentos' cualquier alimento que tenga AL MENOS UNA
    etiqueta prohibida.

    lista_alimentos: lista de dicts, cada uno con al menos:
        {"nombre": "...", "etiquetas": {"lactosa", "alto_sodio", ...}}
    etiquetas_a_evitar: set de etiquetas prohibidas (viene de etiquetas_prohibidas())

    Devuelve (alimentos_permitidos, alimentos_excluidos).
    alimentos_excluidos trae también POR QUÉ se excluyó cada uno, útil
    para mostrarle al usuario o para debug.
    """
    permitidos = []
    excluidos = []

    # Alergias personalizadas (las que empiezan con "custom:")
    palabras_prohibidas = [
        etiqueta.split("custom:", 1)[1]
        for etiqueta in etiquetas_a_evitar
        if etiqueta.startswith("custom:")
    ]

    for alimento in lista_alimentos:
        etiquetas_alimento = set(alimento.get("etiquetas", []))
        choque = etiquetas_alimento & etiquetas_a_evitar

        # Revisamos si el nombre (español o inglés) o los ingredientes
        # mencionan alguna alergia personalizada, como palabra completa.
        texto_alimento = " ".join([
            alimento.get("nombre", "") or "",
            alimento.get("nombre_usda", "") or "",
            alimento.get("ingredientes", "") or "",
        ])
        for palabra in palabras_prohibidas:
            if contiene_palabra(texto_alimento, palabra):
                choque.add(f"alergia:{palabra}")

        if choque:
            excluidos.append({**alimento, "motivo_exclusion": sorted(choque)})
        else:
            permitidos.append(alimento)

    return permitidos, excluidos


# --- Modo de prueba: correr este archivo directo con datos de ejemplo ---
if __name__ == "__main__":
    alimentos_ejemplo = [
        {"nombre": "Pechuga de pollo",       "etiquetas": set()},
        {"nombre": "Leche entera",           "etiquetas": {"lactosa"}},
        {"nombre": "Pan de trigo",           "etiquetas": {"gluten"}},
        {"nombre": "Almendras",              "etiquetas": {"frutos_secos"}},
        {"nombre": "Camarones",              "etiquetas": {"mariscos"}},
        {"nombre": "Papas fritas de bolsa",  "etiquetas": {"alto_sodio"}},
        {"nombre": "Refresco de cola",       "etiquetas": {"alto_azucar"}},
        {"nombre": "Arroz blanco",           "etiquetas": set()},
        {"nombre": "Plátano",                "etiquetas": {"alto_potasio"}},
        {"nombre": "Huevo cocido",           "etiquetas": {"huevo"}},
    ]

    prohibidas, avisos = etiquetas_prohibidas(
        enfermedades=["diabetes"],
        alergias=["lacteos"],
    )

    print("Etiquetas prohibidas para esta persona:", prohibidas)
    if avisos:
        print("\nAvisos de revisión manual:")
        for aviso in avisos:
            print(f"  - {aviso}")

    permitidos, excluidos = filtrar_alimentos(alimentos_ejemplo, prohibidas)

    print(f"\n=== Alimentos PERMITIDOS ({len(permitidos)}) ===")
    for a in permitidos:
        print(f"  {a['nombre']}")

    print(f"\n=== Alimentos EXCLUIDOS ({len(excluidos)}) ===")
    for a in excluidos:
        print(f"  {a['nombre']}  (por: {', '.join(a['motivo_exclusion'])})")

    print("\n--- Segunda prueba: caso con 'Otra' enfermedad ---")
    prohibidas2, avisos2 = etiquetas_prohibidas(
        enfermedades=["hipotiroidismo", "otra"],
        alergias=["ninguna"],
    )
    print("Etiquetas prohibidas:", prohibidas2)
    for aviso in avisos2:
        print(f"  - {aviso}")