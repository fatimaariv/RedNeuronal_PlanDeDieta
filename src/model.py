"""
model.py

Este archivo define la ARQUITECTURA de la red neuronal (cuantas capas,
cuantas neuronas, como aprende). No entrena nada todavia -- eso lo hace
train.py, que va a importar la funcion crear_modelo() de aqui.

Piensa en este archivo como el "plano" de la red, antes de construirla.
"""

from tensorflow.keras.models import Sequential  # type: ignore
from tensorflow.keras.layers import Dense, Input, Dropout  # type: ignore


def crear_modelo(num_entradas, num_salidas):
    """
    Crea la arquitectura de la red neuronal para predecir
    calorías y macronutrientes (regresión, no clasificación).

    num_entradas: cuántas columnas tiene X (features ya procesadas)
    num_salidas: cuántos valores va a predecir (4: calorías, proteína, carbos, grasas)
    """
    modelo = Sequential([
        Input(shape=(num_entradas,)),

        Dense(64, activation='relu'),
        Dropout(0.2),

        Dense(32, activation='relu'),
        Dropout(0.2),

        Dense(16, activation='relu'),
        Dropout(0.2),

        # Capa de salida: SIN activación (lineal), porque es regresión
        # y los valores (calorías, gramos) pueden ser cualquier número positivo
        Dense(num_salidas, activation='linear')
    ])

    modelo.compile(
        optimizer='adam',
        loss='mse',           # Mean Squared Error: estándar para regresión
        metrics=['mae']       # Mean Absolute Error: más fácil de interpretar
    )

    return modelo


if __name__ == "__main__":
    # Esto es solo para probar que el modelo se arma bien,
    # sin necesidad de tener los datos reales todavia.
    modelo_prueba = crear_modelo(num_entradas=13, num_salidas=4)
    modelo_prueba.summary()