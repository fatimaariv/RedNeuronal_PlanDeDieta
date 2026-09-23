"""
debug_usda.py

Script de diagnóstico, NO es parte del proyecto final. Solo sirve para
revisar qué está devolviendo usda_api.py ahora mismo -- en particular,
si info_nutricional ya trae proteina_g/carbohidratos_g/grasas_g o si
siguen saliendo en None (lo que dejaría vacío el pool en plan_semanal.py).

Cómo correrlo:
    python3 src/debug_usda.py
"""

from usda_api import buscar_y_convertir

alimentos = buscar_y_convertir("chicken breast", page_size=3)

print(f"Se encontraron {len(alimentos)} alimentos.\n")

for alimento in alimentos:
    print(f"Nombre: {alimento['nombre']}")
    print(f"  etiquetas: {alimento['etiquetas']}")
    print(f"  info_nutricional: {alimento['info_nutricional']}")
    print()