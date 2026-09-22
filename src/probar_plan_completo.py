"""
probar_plan_completo.py

Prueba el flujo completo: red neuronal (predict.py) + lógica de
horarios (horarios.py) juntos, con una persona de ejemplo.

No modifica ni predict.py ni horarios.py — solo los usa.

Cómo correrlo:
    python3 src/probar_plan_completo.py
"""

from predict import predecir_usuario
from horarios import armar_plan_dia

resultado = predecir_usuario(
    edad=25, sexo="mujer", altura_cm=165, peso_kg=60,
    nivel_actividad="moderado", objetivo="bajar"
)

plan = armar_plan_dia(
    resultado_red=resultado,
    hora_despertar="07:00",
    hora_dormir="23:00",
    actividades=[
        {"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"},
    ],
    num_comidas=4,
)

print("=== Predicción de la red ===")
print(resultado)

print("\n=== Plan de comidas ===")
for comida in plan:
    print(f"{comida['hora']}  {comida['comida']}: "
          f"{comida['calorias_diarias']} kcal")