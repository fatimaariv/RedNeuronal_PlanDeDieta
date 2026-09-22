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
            avisos.append(f"Alergia no reconocida: '{alergia}'. Revisar manualmente.")
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

    for alimento in lista_alimentos:
        etiquetas_alimento = set(alimento.get("etiquetas", []))
        choque = etiquetas_alimento & etiquetas_a_evitar
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