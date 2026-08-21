"""
generar_datos.py

Este script CREA una tabla (CSV) con miles de "personas inventadas"
y calcula sus calorias y macros correctos usando una formula real de
nutricion (Mifflin-St Jeor). Esta tabla es la que se usa despues para
ENTRENAR la red neuronal.

Como correrlo:
    python generar_datos.py

Que hace al terminar:
    Crea el archivo: Datos/raw/dataset_dietas.csv
"""

import random
import csv
import os

# ---------------------------------------------------------
# 1. Configuracion: cuantas "personas de ejemplo" generar
# ---------------------------------------------------------
NUM_PERSONAS = 5000  # entre mas, mejor aprende la red (pero tarda mas)

NIVELES_ACTIVIDAD = {
    "sedentario": 1.2,
    "ligero": 1.375,
    "moderado": 1.55,
    "intenso": 1.725,
    "muy_intenso": 1.9,
}

OBJETIVOS = {
    "bajar": -500,      # déficit de 500 kcal/dia
    "mantener": 0,
    "subir": 400,       # superávit de 400 kcal/dia
}

SEXOS = ["hombre", "mujer"]


def calcular_calorias_base(peso_kg, altura_cm, edad, sexo):
    """
    Formula de Mifflin-St Jeor para calcular el metabolismo basal (BMR).
    Es una formula real y validada, usada por nutriologos.
    """
    if sexo == "hombre":
        return (10 * peso_kg) + (6.25 * altura_cm) - (5 * edad) + 5
    else:  # mujer
        return (10 * peso_kg) + (6.25 * altura_cm) - (5 * edad) - 161


def calcular_macros(calorias_totales):
    """
    Reparte las calorias totales en proteina, carbohidratos y grasas.
    Reparticion estandar: 30% proteina, 40% carbohidratos, 30% grasas.
    (1g proteina = 4 kcal, 1g carbohidrato = 4 kcal, 1g grasa = 9 kcal)
    """
    proteina_g = (calorias_totales * 0.30) / 4
    carbohidratos_g = (calorias_totales * 0.40) / 4
    grasas_g = (calorias_totales * 0.30) / 9
    return round(proteina_g, 1), round(carbohidratos_g, 1), round(grasas_g, 1)


def generar_persona():
    """Genera una persona inventada con datos realistas al azar."""
    edad = random.randint(18, 65)
    sexo = random.choice(SEXOS)
    altura_cm = round(random.uniform(150, 195), 1)
    peso_kg = round(random.uniform(45, 110), 1)
    nivel_actividad = random.choice(list(NIVELES_ACTIVIDAD.keys()))
    objetivo = random.choice(list(OBJETIVOS.keys()))

    # Calculo real usando la formula
    bmr = calcular_calorias_base(peso_kg, altura_cm, edad, sexo)
    calorias_mantenimiento = bmr * NIVELES_ACTIVIDAD[nivel_actividad]
    calorias_finales = calorias_mantenimiento + OBJETIVOS[objetivo]
    calorias_finales = max(calorias_finales, 1200)  # nunca bajar de 1200 kcal (seguridad)

    proteina, carbohidratos, grasas = calcular_macros(calorias_finales)

    return {
        "edad": edad,
        "sexo": sexo,
        "altura_cm": altura_cm,
        "peso_kg": peso_kg,
        "nivel_actividad": nivel_actividad,
        "objetivo": objetivo,
        "calorias_diarias": round(calorias_finales, 1),
        "proteina_g": proteina,
        "carbohidratos_g": carbohidratos,
        "grasas_g": grasas,
    }


def main():
    carpeta_salida = "Datos/raw"
    os.makedirs(carpeta_salida, exist_ok=True)
    ruta_archivo = os.path.join(carpeta_salida, "dataset_dietas.csv")

    columnas = [
        "edad", "sexo", "altura_cm", "peso_kg", "nivel_actividad",
        "objetivo", "calorias_diarias", "proteina_g", "carbohidratos_g", "grasas_g",
    ]

    with open(ruta_archivo, mode="w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for _ in range(NUM_PERSONAS):
            escritor.writerow(generar_persona())

    print(f"Listo. Se generaron {NUM_PERSONAS} personas de ejemplo.")
    print(f"Archivo creado en: {ruta_archivo}")


if __name__ == "__main__":
    main()