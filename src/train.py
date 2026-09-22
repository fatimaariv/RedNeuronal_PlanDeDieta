"""
train.py

Este archivo ENTRENA la red neuronal usando los datos ya procesados
(Datos/processed/) y la arquitectura definida en model.py.

No define la arquitectura (eso es tarea de model.py) y no genera datos
(eso es tarea de generar_datos.py) — solo entrena y guarda el resultado.

Cómo correrlo:
    python3 src/train.py
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error
from model import crear_modelo


# --- 1. Cargar los datos ya procesados ---
# Estos archivos los generó preprocessing.py en el paso anterior.
# Ya vienen limpios, convertidos a número y normalizados —
# aquí NO se debe volver a tocar ni transformar nada.
X_train = pd.read_csv('Datos/processed/X_train.csv')
X_test = pd.read_csv('Datos/processed/X_test.csv')
y_train = pd.read_csv('Datos/processed/y_train.csv')
y_test = pd.read_csv('Datos/processed/y_test.csv')

# Convertimos de DataFrame de pandas a array de NumPy,
# porque TensorFlow espera arrays numéricos, no tablas con nombres de columna.
X_train = X_train.values
X_test = X_test.values
y_train = y_train.values
y_test = y_test.values


# --- 2. Crear el modelo (la arquitectura vacía, sin entrenar) ---
# num_entradas = cuántas columnas tiene X (features de cada persona)
# num_salidas = cuántas columnas tiene y (calorías, proteína, carbos, grasas = 4)
num_entradas = X_train.shape[1]
num_salidas = y_train.shape[1]

modelo = crear_modelo(num_entradas, num_salidas)

# Muestra en la terminal un resumen de las capas, para confirmar
# que la arquitectura se armó como esperábamos antes de entrenar.
modelo.summary()


# --- 3. Entrenar el modelo ---
# fit() es donde realmente "aprende": ajusta sus pesos internos
# repetidamente para que su predicción se acerque a los valores reales de y_train.
historial = modelo.fit(
    X_train, y_train,

    # epochs = cuántas veces la red ve TODO el dataset de entrenamiento completo.
    # 100 es un punto de partida razonable para datos sintéticos simples.
    epochs=100,

    # batch_size = cuántas filas ve la red antes de actualizar sus pesos una vez.
    # 32 es un valor estándar: ni muy lento (batch_size=1) ni muy brusco (todo junto).
    batch_size=32,

    # validation_split reserva automáticamente el 20% del X_train/y_train
    # (no del X_test) para ir midiendo, en cada epoch, si el modelo mejora
    # también en datos que NO está usando para ajustarse. Ojo: el X_test
    # sigue completamente aparte, para la evaluación final.
    validation_split=0.2,

    # verbose=1 imprime el progreso de cada epoch en la terminal
    # (útil para ver si el modelo va mejorando o se estanca).
    verbose=1
)


# --- 4. Evaluar qué tan bien quedó, usando datos que NUNCA vio ---
# Aquí es donde entra X_test/y_test: mide el desempeño real del modelo
# en datos completamente nuevos, para saber si de verdad aprendió
# el patrón o solo memorizó el entrenamiento.
perdida, mae = modelo.evaluate(X_test, y_test, verbose=0)
print(f"\nResultado en datos de prueba:")
print(f"  Error cuadrático medio (loss/mse): {perdida:.2f}")
print(f"  Error absoluto promedio (mae): {mae:.2f}")
# El 'mae' es el número más fácil de leer: en promedio, ¿cuántas
# calorías/gramos de diferencia hay entre lo que predijo y lo real?


# --- 4.5. ⭐ NUEVO: Evaluación detallada, error POR CADA salida por separado ---
# El mae de arriba es un PROMEDIO de las 4 salidas juntas (calorías, proteína,
# carbohidratos, grasas). Eso puede esconder un problema: como calorías es un
# número mucho más grande que los gramos de macros, un error de "32" en
# promedio podría significar que calorías está casi perfecto pero grasas
# está muy mal (o viceversa). Aquí lo separamos para ver la realidad.
predicciones = modelo.predict(X_test, verbose=0)

nombres_salidas = ["calorias_diarias", "proteina_g", "carbohidratos_g", "grasas_g"]
mae_por_salida = mean_absolute_error(y_test, predicciones, multioutput='raw_values')

print("\nError promedio (MAE) por cada valor que predice la red:")
for nombre, error in zip(nombres_salidas, mae_por_salida):
    print(f"  {nombre}: {error:.2f}")

# Ver el error como PORCENTAJE del valor típico, no solo el número absoluto
print("\nError como % del valor promedio real (más fácil de comparar entre macros):")
promedios_reales = y_test.mean(axis=0)
for nombre, error, promedio in zip(nombres_salidas, mae_por_salida, promedios_reales):
    porcentaje = (error / promedio) * 100
    print(f"  {nombre}: {porcentaje:.1f}% de error (promedio real: {promedio:.1f})")


# --- 5. Guardar el modelo ya entrenado ---
# Se guarda en models/ para que predict.py lo pueda cargar después
# SIN tener que reentrenar cada vez que alguien quiera usarlo.
modelo.save('models/modelo_dieta.keras')
print("\nModelo guardado en models/modelo_dieta.keras")