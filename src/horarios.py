"""
horarios.py

Este archivo NO es parte de la red neuronal. Toma el resultado que ya
predijo la red (calorías y macros TOTALES del día) y lo combina con el
horario de actividades de la persona (estudio, trabajo, deporte, sueño)
para decidir A QUÉ HORA come y CUÁNTO le toca comer en cada comida.

    La red neuronal responde "cuánto necesita al día".
    Este archivo responde "cuándo y en qué proporción se reparte ese total".

Trabaja UN DÍA a la vez, porque el horario puede variar por día
(ver sección 5 de la guía). Para armar la semana completa, se llama
armar_plan_dia() una vez por cada día con las actividades de ese día.

Cómo correrlo (modo de prueba, con datos de ejemplo):
    python3 src/horarios.py
"""

REPARTO_COMIDAS = {
    3: {
        "desayuno": 0.30,
        "comida": 0.40,
        "cena": 0.30,
    },
    4: {
        "desayuno": 0.25,
        "comida": 0.35,
        "snack": 0.15,
        "cena": 0.25,
    },
    5: {
        "desayuno": 0.20,
        "snack_manana": 0.10,
        "comida": 0.30,
        "snack_tarde": 0.15,
        "cena": 0.25,
    },
}

_ORDEN_TIPICO = ["desayuno", "snack_manana", "comida", "snack", "snack_tarde", "cena"]


def _a_minutos(hora_str):
    """Convierte 'HH:MM' a minutos desde medianoche."""
    h, m = map(int, hora_str.split(":"))
    return h * 60 + m


def _a_hora_str(minutos):
    """Convierte minutos desde medianoche de vuelta a 'HH:MM'."""
    minutos = int(round(minutos)) % (24 * 60)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _normalizar_bloques(bloques, inicio_dia, fin_dia):
    """
    Convierte una lista de {"inicio": "HH:MM", "fin": "HH:MM"} a minutos,
    recorta lo que cae fuera del rango despierto, y maneja el caso de
    cruzar medianoche (igual que hora_dormir).
    """
    normalizados = []
    for b in bloques:
        ini = _a_minutos(b["inicio"])
        fin = _a_minutos(b["fin"])
        if fin <= ini:
            fin += 24 * 60
        ini = max(ini, inicio_dia)
        fin = min(fin, fin_dia)
        if ini < fin:
            normalizados.append((ini, fin))
    return sorted(normalizados)


def _restar_intervalos(bloques, huecos):
    """
    Resta un conjunto de intervalos (huecos, ej. descansos) de otro
    conjunto (bloques, ej. actividades). Devuelve los pedazos de
    'bloques' que SOBREVIVEN después de quitarles lo que se traslapa
    con 'huecos'.
    """
    resultado = []
    huecos = sorted(huecos)
    for b_ini, b_fin in bloques:
        cursor = b_ini
        for h_ini, h_fin in huecos:
            h_ini_c = max(h_ini, b_ini)
            h_fin_c = min(h_fin, b_fin)
            if h_ini_c >= h_fin_c:
                continue
            if h_ini_c > cursor:
                resultado.append((cursor, h_ini_c))
            cursor = max(cursor, h_fin_c)
        if cursor < b_fin:
            resultado.append((cursor, b_fin))
    return resultado


def calcular_ventanas_libres(hora_despertar, hora_dormir, actividades, descansos=None):
    """
    Calcula los huecos de tiempo LIBRE que tiene la persona ese día:
    horas despierta, menos actividades (estudio/trabajo/deporte),
    MÁS los descansos que "abren" un hueco libre dentro de una actividad.

    Devuelve una lista de dicts:
        {"inicio": min, "fin": min, "es_descanso": bool}

    'es_descanso' es True cuando esa ventana libre cae COMPLETA dentro de
    una actividad original (es decir, existe solo gracias a un descanso
    explícito, no porque fuera tiempo libre normal del día). Esto se usa
    después para GARANTIZARLE al menos una comida, sin importar qué tan
    chica sea comparada con el resto del día.
    """
    descansos = descansos or []

    inicio_dia = _a_minutos(hora_despertar)
    fin_dia = _a_minutos(hora_dormir)
    if fin_dia <= inicio_dia:
        fin_dia += 24 * 60

    bloques_originales = _normalizar_bloques(actividades, inicio_dia, fin_dia)
    huecos = _normalizar_bloques(descansos, inicio_dia, fin_dia)

    bloques = _restar_intervalos(bloques_originales, huecos)

    ventanas_libres = []
    cursor = inicio_dia
    for ini, fin in bloques:
        if ini > cursor:
            ventanas_libres.append((cursor, ini))
        cursor = max(cursor, fin)

    if cursor < fin_dia:
        ventanas_libres.append((cursor, fin_dia))

    # Marcar cuáles ventanas libres existen solo por un descanso: son las
    # que caen COMPLETAS dentro de alguna actividad original.
    resultado = []
    for ini, fin in ventanas_libres:
        es_descanso = any(
            ini >= b_ini and fin <= b_fin for b_ini, b_fin in bloques_originales
        )
        resultado.append({"inicio": ini, "fin": fin, "es_descanso": es_descanso})

    return resultado


def calcular_horas_comida(hora_despertar, hora_dormir, actividades, num_comidas, descansos=None):
    """
    Decide a qué hora cae cada comida del día.

    Estrategia:
      1. Calcular las horas LIBRES del día (huecos entre actividades,
         incluyendo los descansos abiertos dentro de ellas).
      2. GARANTIZAR al menos una comida en cada ventana marcada como
         'es_descanso' (fueron abiertas a propósito, no deben perderse
         aunque sean chicas comparadas con el resto del día).
      3. Repartir las comidas restantes entre TODAS las ventanas,
         proporcional al tamaño de cada una (método de "mayor resto").
      4. Dentro de cada ventana, espaciar sus comidas de forma pareja.
    """
    ventanas = calcular_ventanas_libres(hora_despertar, hora_dormir, actividades, descansos)

    if not ventanas:
        raise ValueError(
            "No quedan horas libres en el día para comer: revisa que las "
            "actividades no cubran TODO el rango entre hora_despertar y hora_dormir, "
            "o agrega un descanso dentro de alguna actividad."
        )

    num_descansos = sum(1 for v in ventanas if v["es_descanso"])
    if num_descansos > num_comidas:
        raise ValueError(
            f"Hay {num_descansos} descansos marcados pero solo {num_comidas} "
            "comidas configuradas: sube num_comidas o quita algún descanso."
        )

    # Paso 2: asignar la comida garantizada a cada descanso
    comidas_por_ventana = [1 if v["es_descanso"] else 0 for v in ventanas]
    restantes = num_comidas - num_descansos

    # Paso 3: repartir lo que queda, proporcional al tamaño de cada ventana
    # (una ventana de descanso también puede recibir comidas EXTRA si es
    # grande; lo único garantizado es el mínimo de 1).
    if restantes > 0:
        duracion_total = sum(v["fin"] - v["inicio"] for v in ventanas)
        restos = []
        asignadas = 0
        extra_por_ventana = []
        for v in ventanas:
            exacto = ((v["fin"] - v["inicio"]) / duracion_total) * restantes
            entero = int(exacto)
            extra_por_ventana.append(entero)
            restos.append(exacto - entero)
            asignadas += entero

        faltan = restantes - asignadas
        orden_por_resto = sorted(range(len(ventanas)), key=lambda i: restos[i], reverse=True)
        for i in orden_por_resto[:faltan]:
            extra_por_ventana[i] += 1

        comidas_por_ventana = [
            base + extra for base, extra in zip(comidas_por_ventana, extra_por_ventana)
        ]

    # Paso 4: espaciar parejo las comidas dentro de cada ventana
    horas = []
    for v, n in zip(ventanas, comidas_por_ventana):
        if n == 0:
            continue
        ini, fin = v["inicio"], v["fin"]
        paso = (fin - ini) / (n + 1)
        for k in range(1, n + 1):
            horas.append(ini + paso * k)

    horas.sort()
    return [_a_hora_str(h) for h in horas]


def nombres_comidas(num_comidas):
    """Devuelve los nombres de comida en orden lógico, según cuántas se usan (3, 4 o 5)."""
    if num_comidas not in REPARTO_COMIDAS:
        raise ValueError("num_comidas debe ser 3, 4 o 5.")
    nombres = list(REPARTO_COMIDAS[num_comidas].keys())
    return sorted(nombres, key=lambda n: _ORDEN_TIPICO.index(n))


def repartir_macros(resultado_red, num_comidas):
    """
    Reparte el total de calorías/macros que predijo la red neuronal
    entre las comidas del día, según REPARTO_COMIDAS.
    """
    if num_comidas not in REPARTO_COMIDAS:
        raise ValueError("num_comidas debe ser 3, 4 o 5.")

    tabla = REPARTO_COMIDAS[num_comidas]
    return {
        nombre_comida: {
            clave: round(valor * porcentaje, 1)
            for clave, valor in resultado_red.items()
        }
        for nombre_comida, porcentaje in tabla.items()
    }


def armar_plan_dia(resultado_red, hora_despertar, hora_dormir, actividades, num_comidas, descansos=None):
    """
    Junta todo: decide a qué hora come la persona y cuánto le toca en
    cada comida, para UN día.
    """
    horas = calcular_horas_comida(hora_despertar, hora_dormir, actividades, num_comidas, descansos)
    nombres = nombres_comidas(num_comidas)
    macros_por_comida = repartir_macros(resultado_red, num_comidas)

    plan = []
    for nombre, hora in zip(nombres, horas):
        fila = {"comida": nombre, "hora": hora}
        fila.update(macros_por_comida[nombre])
        plan.append(fila)
    return plan


if __name__ == "__main__":
    resultado_ejemplo = {
        "calorias_diarias": 1800.0,
        "proteina_g": 135.0,
        "carbohidratos_g": 180.0,
        "grasas_g": 60.0,
    }

    actividades_ejemplo = [
        {"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"},
        {"nombre": "deporte", "inicio": "18:30", "fin": "19:30"},
    ]

    descansos_ejemplo = [
        {"nombre": "comida_trabajo", "inicio": "13:00", "fin": "13:30"},
    ]

    plan = armar_plan_dia(
        resultado_red=resultado_ejemplo,
        hora_despertar="07:00",
        hora_dormir="23:00",
        actividades=actividades_ejemplo,
        num_comidas=4,
        descansos=descansos_ejemplo,
    )

    print("=== Plan de comidas del día (ejemplo) ===\n")
    for comida in plan:
        print(
            f"{comida['hora']}  {comida['comida']:<15} "
            f"{comida['calorias_diarias']:>6.1f} kcal | "
            f"P {comida['proteina_g']:>5.1f}g | "
            f"C {comida['carbohidratos_g']:>5.1f}g | "
            f"G {comida['grasas_g']:>5.1f}g"
        )