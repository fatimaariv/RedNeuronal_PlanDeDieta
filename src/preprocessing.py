"""
preprocessing.py

Este script toma el CSV "crudo" (Datos/raw/dataset_dietas.csv) y lo deja
LISTO para entrenar la red neuronal:
    1. Convierte texto en numeros (sexo, nivel_actividad, objetivo)
    2. Normaliza los numeros (los pone en una escala parecida)
    3. Separa los datos en entradas (X) y salidas (y)
    4. Divide en entrenamiento y prueba
    5. Guarda todo listo en Datos/processed/

Como correrlo:
    python3 src/preprocessing.py

Que hace al terminar:
    Crea varios archivos dentro de Datos/processed/ listos para train.py
"""

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
import joblib

RUTA_ENTRADA = "Datos/raw/dataset_dietas.csv"
CARPETA_SALIDA = "Datos/processed"


def cargar_datos():
    """Lee el CSV crudo y lo devuelve como DataFrame de pandas."""
    df = pd.read_csv(RUTA_ENTRADA)
    print(f"Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
    return df


def limpiar_datos(df):
    """Quita filas con datos faltantes o valores imposibles."""
    filas_antes = len(df)

    df = df.dropna()  # quita filas con datos vacíos
    df = df[(df["edad"] > 0) & (df["edad"] < 100)]
    df = df[(df["peso_kg"] > 20) & (df["peso_kg"] < 300)]
    df = df[(df["altura_cm"] > 100) & (df["altura_cm"] < 250)]
    df = df[df["calorias_diarias"] > 0]

    filas_despues = len(df)
    print(f"Limpieza: se quitaron {filas_antes - filas_despues} filas invalidas")
    return df


def separar_entradas_salidas(df):
    """
    Separa el DataFrame en:
    - X: las columnas que ENTRAN a la red (edad, sexo, altura, peso, actividad, objetivo)
    - y: las columnas que la red debe PREDECIR (calorias, proteina, carbohidratos, grasas)
    """
    columnas_entrada = ["edad", "sexo", "altura_cm", "peso_kg", "nivel_actividad", "objetivo"]
    columnas_salida = ["calorias_diarias", "proteina_g", "carbohidratos_g", "grasas_g"]

    X = df[columnas_entrada].copy()
    y = df[columnas_salida].copy()
    return X, y


def codificar_y_normalizar(X):
    """
    Convierte texto en numeros y normaliza todo.

    - sexo, nivel_actividad, objetivo -> se convierten con OneHotEncoder
      (crea una columna de 0/1 por cada categoria posible)
    - edad, altura_cm, peso_kg -> se normalizan con StandardScaler
      (quedan con promedio 0 y desviacion estandar 1)
    """
    columnas_numericas = ["edad", "altura_cm", "peso_kg"]
    columnas_categoricas = ["sexo", "nivel_actividad", "objetivo"]

    # Normalizar numericas
    scaler = StandardScaler()
    X_numericas = scaler.fit_transform(X[columnas_numericas])
    X_numericas = pd.DataFrame(X_numericas, columns=columnas_numericas)

    # Codificar categoricas (texto -> columnas de 0/1)
    encoder = OneHotEncoder(sparse_output=False)
    X_categoricas = encoder.fit_transform(X[columnas_categoricas])
    nombres_columnas_cat = encoder.get_feature_names_out(columnas_categoricas)
    X_categoricas = pd.DataFrame(X_categoricas, columns=nombres_columnas_cat)

    # Unir todo en una sola tabla lista para la red
    X_listo = pd.concat(
        [X_numericas.reset_index(drop=True), X_categoricas.reset_index(drop=True)],
        axis=1,
    )

    return X_listo, scaler, encoder


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    # 1. Cargar
    df = cargar_datos()

    # 2. Limpiar
    df = limpiar_datos(df)

    # 3. Separar entradas y salidas
    X, y = separar_entradas_salidas(df)

    # 4. Codificar y normalizar entradas
    X_listo, scaler, encoder = codificar_y_normalizar(X)

    # 5. Dividir en entrenamiento (80%) y prueba (20%)
    X_train, X_test, y_train, y_test = train_test_split(
        X_listo, y, test_size=0.2, random_state=42
    )

    # 6. Guardar todo listo para el siguiente paso (train.py)
    X_train.to_csv(f"{CARPETA_SALIDA}/X_train.csv", index=False)
    X_test.to_csv(f"{CARPETA_SALIDA}/X_test.csv", index=False)
    y_train.to_csv(f"{CARPETA_SALIDA}/y_train.csv", index=False)
    y_test.to_csv(f"{CARPETA_SALIDA}/y_test.csv", index=False)

    # Tambien guardamos el scaler y el encoder: se necesitan despues
    # en predict.py para transformar los datos de un usuario NUEVO
    # exactamente igual a como se transformaron estos datos de entrenamiento
    joblib.dump(scaler, f"{CARPETA_SALIDA}/scaler.pkl")
    joblib.dump(encoder, f"{CARPETA_SALIDA}/encoder.pkl")

    print("\nListo. Archivos guardados en Datos/processed/:")
    print(f"  X_train: {X_train.shape}")
    print(f"  X_test:  {X_test.shape}")
    print(f"  y_train: {y_train.shape}")
    print(f"  y_test:  {y_test.shape}")
    print("  scaler.pkl y encoder.pkl (para usarlos despues en predict.py)")


if __name__ == "__main__":
    main()