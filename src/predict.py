"""
predict.py

Este archivo usa el modelo YA ENTRENADO (models/modelo_dieta.keras)
para predecir calorías y macros de UNA PERSONA NUEVA (no del dataset
de entrenamiento).

No entrena nada aquí — eso ya lo hizo train.py. Este archivo solo:
    1. Recibe los datos de una persona nueva
    2. Los transforma EXACTAMENTE igual que en preprocessing.py
       (usando el mismo scaler.pkl y encoder.pkl, no unos nuevos)
    3. Le pasa esos datos ya transformados al modelo
    4. Imprime la predicción de calorías/macros

Cómo correrlo:
    python3 src/predict.py
"""

import pandas as pd
import joblib
from tensorflow.keras.models import load_model  # type: ignore


# --- 1. Cargar el modelo y las herramientas de transformación ---
# El modelo ya entrenado, guardado por train.py.
modelo = load_model('models/modelo_dieta.keras')

# El scaler y encoder son los MISMOS que se usaron para entrenar
# (guardados por preprocessing.py). Es CRUCIAL usar estos mismos,
# no crear unos nuevos, porque el modelo aprendió a leer los números
# en la escala y el orden que estos generan específicamente.
scaler = joblib.load('Datos/processed/scaler.pkl')
encoder = joblib.load('Datos/processed/encoder.pkl')

# Estos deben coincidir EXACTAMENTE con los que se usaron en preprocessing.py
columnas_numericas = ["edad", "altura_cm", "peso_kg"]
columnas_categoricas = ["sexo", "nivel_actividad", "objetivo"]

# Nombres de lo que la red predice, en el mismo orden que y_train/y_test
nombres_salidas = ["calorias_diarias", "proteina_g", "carbohidratos_g", "grasas_g"]


def predecir_usuario(edad, sexo, altura_cm, peso_kg, nivel_actividad, objetivo):
    """
    Recibe los datos de UNA persona (en su forma original, legible por humanos:
    texto para sexo/actividad/objetivo, números normales para edad/altura/peso)
    y devuelve un diccionario con sus calorías y macros predichos.

    Ejemplo de uso:
        resultado = predecir_usuario(
            edad=25, sexo="Mujer", altura_cm=165, peso_kg=60,
            nivel_actividad="Moderado", objetivo="Bajar peso"
        )
    """

    # --- 2. Armar un DataFrame de una sola fila con los datos de la persona ---
    # Se arma como diccionario -> DataFrame para poder usar los mismos
    # métodos de pandas/sklearn que se usaron al entrenar.
    datos_persona = pd.DataFrame([{
        "edad": edad,
        "sexo": sexo,
        "altura_cm": altura_cm,
        "peso_kg": peso_kg,
        "nivel_actividad": nivel_actividad,
        "objetivo": objetivo
    }])

    # --- 3. Transformar las columnas numéricas con el MISMO scaler ---
    # OJO: aquí usamos .transform(), NUNCA .fit_transform(). fit_transform
    # "aprendería" una escala nueva a partir de esta sola persona, lo cual
    # rompería todo. transform() solo APLICA la escala ya aprendida en
    # preprocessing.py sobre los 5,000 datos de entrenamiento.
    numericas_transformadas = scaler.transform(datos_persona[columnas_numericas])
    numericas_df = pd.DataFrame(numericas_transformadas, columns=columnas_numericas)

    # --- 4. Transformar las columnas de texto con el MISMO encoder ---
    # Igual que arriba: .transform(), no .fit_transform(). El encoder ya
    # "memorizó" cuáles son las categorías válidas (Hombre/Mujer, etc.)
    # y en qué columna de 0/1 convierte cada una.
    categoricas_transformadas = encoder.transform(datos_persona[columnas_categoricas])
    nombres_columnas_cat = encoder.get_feature_names_out(columnas_categoricas)
    categoricas_df = pd.DataFrame(categoricas_transformadas, columns=nombres_columnas_cat)

    # --- 5. Unir todo, en el MISMO orden que se usó al entrenar ---
    # (numéricas primero, categóricas después — igual que en preprocessing.py)
    X_persona = pd.concat([numericas_df, categoricas_df], axis=1)

    # --- 6. Predecir ---
    # El modelo espera un array de NumPy, por eso .values
    prediccion = modelo.predict(X_persona.values, verbose=0)

    # prediccion es un array con 1 fila y 4 columnas (calorías, proteína,
    # carbohidratos, grasas). Tomamos esa única fila con [0].
    resultado = {
        nombre: round(float(valor), 1)
        for nombre, valor in zip(nombres_salidas, prediccion[0])
    }

    return resultado


# --- 7. Ejemplo de uso, para probar que todo funciona ---
# Esto solo corre si ejecutas ESTE archivo directamente
# (no corre si otro archivo hace "from predict import predecir_usuario").
if __name__ == "__main__":
    ejemplo = predecir_usuario(
        edad=25,
        sexo="mujer",
        altura_cm=165,
        peso_kg=60,
        nivel_actividad="moderado",
        objetivo="bajar"
    )

    print("\nPredicción para la persona de ejemplo:")
    for nombre, valor in ejemplo.items():
        print(f"  {nombre}: {valor}")