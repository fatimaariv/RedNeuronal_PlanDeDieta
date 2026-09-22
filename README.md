Archivo	Función	Estado
generar_datos.py	Crea datos sintéticos de "personas de ejemplo" con sus calorías/macros correctos, usando la fórmula Mifflin-St Jeor.	✅ Hecho
preprocessing.py	Limpia el CSV, convierte texto en números, normaliza, y divide en entrenamiento/prueba.	✅ Hecho
model.py	Define la arquitectura de la red neuronal (cuántas capas, neuronas, etc.).	✅ Hecho
train.py	Entrena la red usando los datos ya procesados y el modelo definido.	✅ Hecho
predict.py	Usa el modelo ya entrenado para predecir los datos de un usuario nuevo real.	✅ Hecho

Paso 8 — Definir la arquitectura, entrenar y predecir (model.py, train.py, predict.py)
Se definió una red neuronal con 3 capas ocultas (64→32→16 neuronas, activación ReLU, con
Dropout del 20% para evitar sobreajuste) y una capa de salida de 4 neuronas sin activación
(porque es un problema de regresión, no de clasificación). Se entrenó con los datos de
Datos/processed/ durante 100 epochs.

Resultado en datos de prueba (varía ligeramente cada vez que se reentrena, por la
inicialización aleatoria de la red):
  - Error promedio en calorías: ~2.5%
  - Error promedio en proteína: ~1.6%
  - Error promedio en carbohidratos: ~1.8%
  - Error promedio en grasas: ~3.2%

Se probó con una persona de ejemplo (25 años, mujer, 165cm, 60kg, actividad moderada,
objetivo bajar peso) y la predicción coincidió con el cálculo real de la fórmula
Mifflin-St Jeor con menos de 2% de diferencia.

IMPORTANTE para quien programe el formulario/interfaz (ver sección 5): el modelo
espera los valores de texto EXACTAMENTE como los generó generar_datos.py, es decir
en minúsculas y sin espacios:
  - sexo: "hombre" o "mujer"
  - nivel_actividad: "sedentario", "ligero", "moderado", "intenso", "muy_intenso"
  - objetivo: "bajar", "mantener", "subir"
Si el formulario le muestra al usuario opciones más "bonitas" (ej. "Bajar peso"),
hace falta una tabla de conversión antes de mandarle los datos al modelo.

Cómo correrlo:
    python3 src/train.py     # entrena y guarda el modelo en models/
    python3 src/predict.py   # usa el modelo ya entrenado para una persona de ejemplo
ejemplo

7. Lo que sigue (próximos pasos)
1. Evaluación — Comparar contra un modelo simple (Random Forest) para confirmar que vale la pena usar red neuronal
2. Lógica de horarios y preferencias — Sistema aparte que combina la predicción con horarios, alergias e ingredientes disponibles
3. Integración con API de USDA — Convertir los macros predichos en alimentos reales
4. (Opcional) Interfaz — Formulario visual para que el usuario final interactúe sin usar la terminal