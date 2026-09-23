"""
Script temporal de diagnóstico: muestra la descripción e ingredientes
CRUDOS que manda USDA para cada resultado, para confirmar si las
etiquetas de alérgenos (lactosa/gluten/soya) son correctas o falsas
por tratarse de productos procesados en vez de pollo simple.
"""
from usda_api import buscar_alimentos

resultados = buscar_alimentos("chicken breast", page_size=3)

for r in resultados:
    print("Nombre:", r.get("description"))
    print("Ingredientes:", r.get("ingredients"))
    print()
