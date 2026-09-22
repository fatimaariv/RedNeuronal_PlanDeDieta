"""
comparar_modelos.py

Este archivo NO entrena nada nuevo de la red neuronal ni la modifica.
Su único trabajo es responder una pregunta: ¿de verdad valía la pena
usar una red neuronal, o un modelo más simple (Random Forest) da
resultados iguales o mejores?

Compara:
    - La red neuronal ya entrenada (models/modelo_dieta.keras)
    - Un Random Forest entrenado aquí mismo, con los MISMOS datos

Cómo correrlo:
    python3 src/comparar_modelos.py
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from tensorflow.keras.models import load_model  # type: ignore


# --- 1. Cargar los MISMOS datos que usó la red neuronal ---
# Es crucial que sea exactamente el mismo X_train/X_test/y_train/y_test,
# para que la comparación sea justa (mismos datos, mismo split).
X_train = pd.read_csv('Datos/processed/X_train.csv').values
X_test = pd.read_csv('Datos/processed/X_test.csv').values
y_train = pd.read_csv('Datos/processed/y_train.csv').values
y_test = pd.read_csv('Datos/processed/y_test.csv').values

nombres_salidas = ["calorias_diarias", "proteina_g", "carbohidratos_g", "grasas_g"]


# --- 2. Cargar la red neuronal YA entrenada (no se reentrena aquí) ---
red_neuronal = load_model('models/modelo_dieta.keras')


# --- 3. Entrenar un Random Forest con los mismos datos ---
# RandomForestRegressor puede predecir varias salidas a la vez (calorías,
# proteína, carbohidratos, grasas) de forma nativa, sin necesitar ninguna
# arquitectura especial como sí necesita una red neuronal.
#
# n_estimators=200: cuántos "árboles de decisión" arma el bosque.
# Más árboles = más estable, pero más lento. 200 es un buen punto de partida.
# random_state=42: para que el resultado sea reproducible entre corridas.
random_forest = RandomForestRegressor(n_estimators=200, random_state=42)
random_forest.fit(X_train, y_train)


# --- 4. Predecir con ambos modelos sobre los MISMOS datos de prueba ---
predicciones_red = red_neuronal.predict(X_test, verbose=0)
predicciones_rf = random_forest.predict(X_test)


# --- 5. Comparar el error de cada modelo, salida por salida ---
mae_red = mean_absolute_error(y_test, predicciones_red, multioutput='raw_values')
mae_rf = mean_absolute_error(y_test, predicciones_rf, multioutput='raw_values')

print("=" * 65)
print("COMPARACIÓN: Red Neuronal vs Random Forest")
print("=" * 65)
print(f"{'Salida':<20}{'Red Neuronal (MAE)':<22}{'Random Forest (MAE)':<20}")
print("-" * 65)

for nombre, error_red, error_rf in zip(nombres_salidas, mae_red, mae_rf):
    ganador = "Red Neuronal" if error_red < error_rf else "Random Forest"
    print(f"{nombre:<20}{error_red:<22.2f}{error_rf:<20.2f}  → gana: {ganador}")

print("-" * 65)

# --- 6. Comparación general (promedio de las 4 salidas) ---
mae_red_promedio = mae_red.mean()
mae_rf_promedio = mae_rf.mean()

print(f"\nMAE promedio general:")
print(f"  Red Neuronal:   {mae_red_promedio:.2f}")
print(f"  Random Forest:  {mae_rf_promedio:.2f}")

if mae_red_promedio < mae_rf_promedio:
    diferencia = ((mae_rf_promedio - mae_red_promedio) / mae_rf_promedio) * 100
    print(f"\nConclusión: la Red Neuronal predice mejor en promedio "
          f"(~{diferencia:.1f}% menos error que Random Forest).")
else:
    diferencia = ((mae_red_promedio - mae_rf_promedio) / mae_red_promedio) * 100
    print(f"\nConclusión: Random Forest predice mejor en promedio "
          f"(~{diferencia:.1f}% menos error que la Red Neuronal), "
          f"y es más simple de mantener.")