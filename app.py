import os
import re
import sys
from flask import Flask, render_template, request

# Permitir que app.py importe los módulos dentro de src/ sin errores de ruta
RUTA_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if RUTA_SRC not in sys.path:
    sys.path.insert(0, RUTA_SRC)

from plan_semanal import generar_plan_semana, CATEGORIA_ES

app = Flask(__name__)

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

# Nombre con acentos para mostrar en las pestañas (las claves se quedan sin
# acento porque también se usan como id en el HTML).
NOMBRES_DIA = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}

# Valores válidos (los mismos con los que se entrenó la red) y rangos que
# también pide el formulario. Se validan aquí porque el navegador se puede
# saltar (o el formulario se puede enviar sin él).
SEXOS_VALIDOS = {"hombre", "mujer"}
ACTIVIDADES_VALIDAS = {"sedentario", "ligero", "moderado", "intenso", "muy_intenso"}
OBJETIVOS_VALIDOS = {"bajar", "mantener", "subir"}
RANGO_EDAD = (15, 100)
RANGO_PESO = (30, 250)
RANGO_ALTURA = (120, 230)
COMIDAS_VALIDAS = {3, 4, 5}
PATRON_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _error(mensaje):
    return render_template("index.html", error=mensaje)


def _leer_hora(nombre_campo, etiqueta, por_defecto):
    """
    Lee un campo <input type="time">. Si el campo no viene en el formulario
    usa el valor por defecto; si viene vacío o mal escrito lanza ValueError
    con un mensaje que dice qué campo revisar.
    """
    valor = request.form.get(nombre_campo)
    if valor is None:
        return por_defecto
    valor = valor.strip()
    if not PATRON_HORA.match(valor):
        raise ValueError(f"Falta o no es válida la hora de «{etiqueta}» (formato HH:MM).")
    return valor

NOMBRES_COMIDA_BONITOS = {
    "desayuno": "Desayuno",
    "comida": "Comida",
    "cena": "Cena",
    "snack": "Snack",
    "snack_manana": "Snack (Mañana)",
    "snack_tarde": "Snack (Tarde)",
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predecir", methods=["POST"])
def predecir():
    # 1. Validar y obtener datos físicos y objetivo (para la Red Neuronal)
    edad_raw = request.form.get("edad")
    altura_raw = request.form.get("altura") or request.form.get("altura_cm")
    peso_raw = request.form.get("peso") or request.form.get("peso_kg")

    if not all([edad_raw, altura_raw, peso_raw]):
        return render_template(
            "index.html",
            error="Por favor completa todos los campos biométricos (edad, peso y altura)."
        )

    try:
        edad = int(edad_raw)
        altura_cm = float(altura_raw)
        peso_kg = float(peso_raw)
    except ValueError:
        return render_template(
            "index.html",
            error="Los valores de edad, peso y altura deben ser números válidos."
        )

    for valor, (minimo, maximo), texto in [
        (edad, RANGO_EDAD, "La edad"),
        (peso_kg, RANGO_PESO, "El peso (kg)"),
        (altura_cm, RANGO_ALTURA, "La altura (cm)"),
    ]:
        if not (minimo <= valor <= maximo):
            return _error(f"{texto} debe estar entre {minimo} y {maximo}.")

    sexo = request.form.get("sexo", "mujer").strip().lower()
    nivel_actividad = (
        request.form.get("actividad")
        or request.form.get("nivel_actividad")
        or "moderado"
    ).strip().lower()
    objetivo = request.form.get("objetivo", "mantener").strip().lower()

    if sexo not in SEXOS_VALIDOS:
        return _error("Selecciona un sexo válido (Mujer u Hombre).")
    if nivel_actividad not in ACTIVIDADES_VALIDAS:
        return _error("Selecciona un nivel de actividad física de la lista.")
    if objetivo not in OBJETIVOS_VALIDOS:
        return _error("Selecciona un objetivo de la lista.")

    # Dato adicional del formulario (Sección 5 de la guía)
    embarazo = request.form.get("embarazo", "no")
    trimestre = request.form.get("trimestre", "")

    # 2. Filtros de seguridad (Checklists)
    enfermedades = request.form.getlist("enfermedades")
    alergias = request.form.getlist("alergias")
    # Captura el texto libre de "otra_alergia"
    otra_alergia_texto = request.form.get("otra_alergia", "").strip()

    if "otra" in alergias and otra_alergia_texto:
        alergias.remove("otra")
        alergias_personalizadas = [
            item.strip().lower() for item in otra_alergia_texto.split(",") if item.strip()
        ]
        alergias.extend(alergias_personalizadas)

    # 3. Horarios y rutina
    try:
        num_comidas = int(request.form.get("num_comidas", 4))
    except ValueError:
        num_comidas = None
    if num_comidas not in COMIDAS_VALIDAS:
        return _error("El número de comidas al día debe ser 3, 4 o 5.")

    try:
        hora_despertar = _leer_hora("hora_despertar", "Hora de despertar", "07:00")
        hora_dormir = _leer_hora("hora_dormir", "Hora de dormir", "23:00")

        actividades_base = []
        if request.form.get("tiene_actividad_principal") == "si":
            act_ini = _leer_hora("act_inicio", "Inicio estudio/trabajo", "09:00")
            act_fin = _leer_hora("act_fin", "Fin estudio/trabajo", "17:00")
            actividades_base.append({"nombre": "estudio/trabajo", "inicio": act_ini, "fin": act_fin})

        if request.form.get("hace_deporte") == "si":
            dep_ini = _leer_hora("dep_inicio", "Inicio entrenamiento", "18:30")
            dep_fin = _leer_hora("dep_fin", "Fin entrenamiento", "19:30")
            actividades_base.append({"nombre": "entrenamiento", "inicio": dep_ini, "fin": dep_fin})

        # El descanso solo tiene sentido si estudia o trabaja (en el formulario
        # la pregunta se oculta, pero su valor se seguía enviando).
        descansos_base = []
        if (request.form.get("tiene_actividad_principal") == "si"
                and request.form.get("tiene_descanso") == "si"):
            desc_ini = _leer_hora("desc_inicio", "Inicio descanso", "13:00")
            desc_fin = _leer_hora("desc_fin", "Fin descanso", "13:30")
            descansos_base.append({"nombre": "descanso", "inicio": desc_ini, "fin": desc_fin})
    except ValueError as err:
        return _error(str(err))

    # Armar el diccionario para los 7 días de la semana
    actividades_por_dia = {dia: list(actividades_base) for dia in DIAS_SEMANA}
    descansos_por_dia = {dia: list(descansos_base) for dia in DIAS_SEMANA}

    # Opción de consultar alimentos reales en USDA o hacer solo cálculo rápido
    incluir_usda = request.form.get("incluir_usda") == "si"

    # 4. Ejecutar todo el pipeline conectado
    try:
        resultado_completo = generar_plan_semana(
            edad=edad,
            sexo=sexo,
            altura_cm=altura_cm,
            peso_kg=peso_kg,
            nivel_actividad=nivel_actividad,
            objetivo=objetivo,
            enfermedades=enfermedades,
            alergias=alergias,
            hora_despertar=hora_despertar,
            hora_dormir=hora_dormir,
            num_comidas=num_comidas,
            actividades_por_dia=actividades_por_dia,
            descansos_por_dia=descansos_por_dia,
            incluir_catalogo_usda=incluir_usda,
            asignar_alimentos=incluir_usda,
        )
    except ValueError as err:
        return render_template("index.html", error=str(err))

    # Agregar aviso si marcó embarazo (la red base no fue entrenada con esta variable)
    if sexo == "mujer" and embarazo == "si":
        resultado_completo["avisos_seguridad"].insert(
            0,
            f"Embarazo reportado (Trimestre {trimestre}°): la red neuronal base calcula requerimientos estándar; "
            "un especialista debe ajustar el superávit calórico y micronutrientes."
        )

    return render_template(
        "resultado.html",
        datos=resultado_completo,
        nombres_comida=NOMBRES_COMIDA_BONITOS,
        nombres_dia=NOMBRES_DIA,
        categoria_es=CATEGORIA_ES,
        incluir_usda=incluir_usda,
    )


if __name__ == "__main__":
    # El modo debug solo se activa a propósito (FLASK_DEBUG=1), porque su
    # consola permite ejecutar código en el servidor.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)