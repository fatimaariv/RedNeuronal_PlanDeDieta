import os
import sys
from flask import Flask, render_template, request

# Permitir que app.py importe los módulos dentro de src/ sin errores de ruta
RUTA_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if RUTA_SRC not in sys.path:
    sys.path.insert(0, RUTA_SRC)

from plan_semanal import generar_plan_semana, CATEGORIA_ES

app = Flask(__name__)

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

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

    sexo = request.form.get("sexo", "mujer").strip().lower()
    nivel_actividad = (
        request.form.get("actividad")
        or request.form.get("nivel_actividad")
        or "moderado"
    ).strip().lower()
    objetivo = request.form.get("objetivo", "mantener").strip().lower()

    # Dato adicional del formulario (Sección 5 de la guía)
    embarazo = request.form.get("embarazo", "no")
    trimestre = request.form.get("trimestre", "")

    # 2. Filtros de seguridad (Checklists)
    enfermedades = request.form.getlist("enfermedades")
    alergias = request.form.getlist("alergias")
    # Captura el texto libre de "otra_alergia"
    otra_alergia_texto = request.form.get("otra_alergia", "").strip()

    print("Texto recibido de otra_alergia:", repr(otra_alergia_texto))  # Diagnóstico

    if "otra" in alergias and otra_alergia_texto:
        alergias.remove("otra")
        alergias_personalizadas = [
            item.strip().lower() for item in otra_alergia_texto.split(",") if item.strip()
        ]
        alergias.extend(alergias_personalizadas)

    print("Alergias recibidas:", alergias)

    # 3. Horarios y rutina
    hora_despertar = request.form.get("hora_despertar", "07:00")
    hora_dormir = request.form.get("hora_dormir", "23:00")
    num_comidas = int(request.form.get("num_comidas", 4))

    actividades_base = []
    if request.form.get("tiene_actividad_principal") == "si":
        act_ini = request.form.get("act_inicio", "09:00")
        act_fin = request.form.get("act_fin", "17:00")
        actividades_base.append({"nombre": "trabajo_estudio", "inicio": act_ini, "fin": act_fin})

    if request.form.get("hace_deporte") == "si":
        dep_ini = request.form.get("dep_inicio", "18:30")
        dep_fin = request.form.get("dep_fin", "19:30")
        actividades_base.append({"nombre": "deporte", "inicio": dep_ini, "fin": dep_fin})

    descansos_base = []
    if request.form.get("tiene_descanso") == "si":
        desc_ini = request.form.get("desc_inicio", "13:00")
        desc_fin = request.form.get("desc_fin", "13:30")
        descansos_base.append({"nombre": "descanso_comida", "inicio": desc_ini, "fin": desc_fin})

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
        categoria_es=CATEGORIA_ES,
        incluir_usda=incluir_usda,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)