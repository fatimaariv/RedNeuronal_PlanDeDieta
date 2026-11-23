"""
Pruebas de las correcciones de la revisión (rama correcciones-revision).

Cómo correrlas, desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v

No necesitan Internet ni clave de USDA: las búsquedas a USDA se reemplazan
por un catálogo de prueba con valores aproximados por 100 g.
"""
import os
import sys
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RAIZ)  # los scripts usan rutas relativas (Datos/, models/)
sys.path.insert(0, os.path.join(RAIZ, "src"))
sys.path.insert(0, RAIZ)
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from usda_api import inferir_etiquetas, usda_a_formato_interno  # noqa: E402
from filtros_seguridad import etiquetas_prohibidas, filtrar_alimentos, contiene_palabra  # noqa: E402
from horarios import calcular_horas_comida  # noqa: E402
from predict import predecir_usuario, CALORIAS_MINIMAS  # noqa: E402
import plan_semanal  # noqa: E402
import app as aplicacion  # noqa: E402


def etiquetas(descripcion):
    return inferir_etiquetas({"description": descripcion, "foodNutrients": []})


# Catálogo de prueba en el formato de usda_a_formato_interno (por 100 g).
def _alimento(nombre, nombre_usda, kcal, p, c, g, etiquetas_=()):
    return {"nombre": nombre, "nombre_usda": nombre_usda, "ingredientes": "",
            "etiquetas": set(etiquetas_),
            "info_nutricional": {"calorias": kcal, "proteina_g": p,
                                 "carbohidratos_g": c, "grasas_g": g}}


CATALOGO_PRUEBA = {
    "chicken breast": [_alimento("chicken breast", "Chicken, breast, raw", 165, 31, 0, 3.6)],
    "salmon": [_alimento("salmon", "Fish, salmon, Atlantic, raw", 208, 20, 0, 13)],
    "eggs": [_alimento("eggs", "Eggs, Grade A, Large", 143, 12.6, 0.7, 9.5, {"huevo"})],
    "tofu": [_alimento("tofu", "Tofu, raw", 76, 8, 1.9, 4.8, {"soya"})],
    "lean beef": [_alimento("lean beef", "Beef, ground, 95% lean", 137, 21, 0, 5)],
    "rice": [_alimento("rice", "Rice, white, cooked", 130, 2.7, 28, 0.3)],
    "oats": [_alimento("oats", "Oats", 389, 16.9, 66, 6.9)],
    "potato": [_alimento("potato", "Potatoes, raw", 77, 2, 17, 0.1)],
    "whole wheat bread": [_alimento("whole wheat bread", "Bread, whole-wheat", 247, 13, 41, 3.4, {"gluten"})],
    "quinoa": [_alimento("quinoa", "Quinoa, cooked", 120, 4.4, 21, 1.9)],
    "avocado": [_alimento("avocado", "Avocados, raw", 160, 2, 8.5, 14.7)],
    "olive oil": [_alimento("olive oil", "Oil, olive", 884, 0, 0, 100)],
    "almonds": [_alimento("almonds", "Nuts, almonds", 579, 21, 22, 50, {"frutos_secos"})],
    "peanut butter": [_alimento("peanut butter", "Peanut butter, smooth", 588, 25, 20, 50, {"frutos_secos"})],
    "broccoli": [_alimento("broccoli", "Broccoli, raw", 34, 2.8, 6.6, 0.4)],
    "spinach": [_alimento("spinach", "Spinach, raw", 23, 2.9, 3.6, 0.4)],
    "carrot": [_alimento("carrot", "Carrots, raw", 41, 0.9, 9.6, 0.2)],
    "mixed vegetables": [_alimento("mixed vegetables", "Vegetables, mixed", 65, 2.9, 13, 0.3)],
}


def _buscar_falso(query, page_size=5, api_key=None):
    return [dict(a, etiquetas=set(a["etiquetas"])) for a in CATALOGO_PRUEBA[query]]


class TestAlergenos(unittest.TestCase):
    def test_plurales_se_detectan(self):
        self.assertIn("frutos_secos", etiquetas("Nuts, almonds"))
        self.assertIn("frutos_secos", etiquetas("Peanuts, all types, raw"))
        self.assertIn("frutos_secos", etiquetas("Walnuts"))
        self.assertIn("huevo", etiquetas("Eggs"))
        self.assertIn("mariscos", etiquetas("Crabs"))
        self.assertIn("lactosa", etiquetas("Cheeses"))

    def test_sin_falsos_positivos(self):
        self.assertNotIn("lactosa", etiquetas("Peanut butter, smooth style"))
        self.assertNotIn("lactosa", etiquetas("Almond milk, unsweetened"))
        self.assertNotIn("lactosa", etiquetas("Coconut milk"))
        self.assertNotIn("lactosa", etiquetas("Cream of rice"))
        self.assertNotIn("mariscos", etiquetas("Fish, salmon, Atlantic, raw"))
        self.assertNotIn("frutos_secos", etiquetas("Butternut squash"))

    def test_siguen_detectandose(self):
        self.assertIn("lactosa", etiquetas("Butter, salted"))
        self.assertIn("lactosa", etiquetas("Ice cream, vanilla"))
        self.assertIn("frutos_secos", etiquetas("Peanut butter, smooth style"))
        self.assertIn("soya", etiquetas("Soy milk"))
        self.assertIn("gluten", etiquetas("Bread, whole-wheat"))


class TestEnergia(unittest.TestCase):
    def test_prefiere_kcal_aunque_kj_venga_primero(self):
        j = {"description": "Rice", "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "kJ", "value": 544},
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 130}]}
        self.assertEqual(usda_a_formato_interno(j)["info_nutricional"]["calorias"], 130)

    def test_convierte_si_solo_hay_kj(self):
        j = {"description": "Rice", "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "kJ", "value": 544}]}
        self.assertAlmostEqual(usda_a_formato_interno(j)["info_nutricional"]["calorias"], 130.0, delta=0.5)


class TestMinimoCalorias(unittest.TestCase):
    def test_no_baja_de_1200(self):
        r = predecir_usuario(65, "mujer", 150, 45, "sedentario", "bajar")
        self.assertEqual(r["calorias_diarias"], CALORIAS_MINIMAS)
        # los macros se escalan igual y siguen sumando ~1200 kcal
        kcal_macros = 4 * r["proteina_g"] + 4 * r["carbohidratos_g"] + 9 * r["grasas_g"]
        self.assertAlmostEqual(kcal_macros, 1200, delta=80)

    def test_caso_normal_sin_cambio(self):
        r = predecir_usuario(19, "mujer", 158, 60, "ligero", "subir")
        self.assertEqual(r["calorias_diarias"], 2131.7)


class TestHorarios(unittest.TestCase):
    def test_hora_mal_escrita(self):
        with self.assertRaisesRegex(ValueError, "formato HH:MM"):
            calcular_horas_comida("7", "23:00", [], 4)
        with self.assertRaisesRegex(ValueError, "formato HH:MM"):
            calcular_horas_comida("07:00", "23:00", [{"inicio": "", "fin": "17:00"}], 4)

    def test_despertar_igual_a_dormir(self):
        with self.assertRaisesRegex(ValueError, "igual"):
            calcular_horas_comida("07:00", "07:00", [], 4)

    def test_inicio_igual_a_fin(self):
        with self.assertRaisesRegex(ValueError, "misma hora"):
            calcular_horas_comida("07:00", "23:00", [{"nombre": "trabajo", "inicio": "09:00", "fin": "09:00"}], 4)

    def test_actividad_despues_de_medianoche(self):
        horas = calcular_horas_comida(
            "07:00", "01:30", [{"inicio": "09:00", "fin": "17:00"}, {"inicio": "00:00", "fin": "01:00"}], 5)
        for h in horas:
            self.assertFalse("00:00" <= h < "01:00", f"comida a las {h} durante la actividad")

    def test_turno_nocturno_sigue_funcionando(self):
        horas = calcular_horas_comida("15:00", "07:00", [{"inicio": "22:00", "fin": "06:00"}], 4)
        self.assertEqual(len(horas), 4)


class TestOtraAlergia(unittest.TestCase):
    def test_palabra_completa(self):
        self.assertFalse(contiene_palabra("Papa", "pa"))
        self.assertTrue(contiene_palabra("Avena", "avena"))
        self.assertTrue(contiene_palabra("Salmón", "salmon"))
        self.assertTrue(contiene_palabra("Nueces", "nuez"))

    def test_aviso_y_filtrado(self):
        prohibidas, avisos = etiquetas_prohibidas([], ["fresa", "avena"])
        self.assertEqual(len(avisos), 2)
        alimentos = [{"nombre": "Avena", "nombre_usda": "Oats", "etiquetas": set()},
                     {"nombre": "Papa", "nombre_usda": "Potatoes", "etiquetas": set()}]
        permitidos, excluidos = filtrar_alimentos(alimentos, prohibidas)
        self.assertEqual([a["nombre"] for a in excluidos], ["Avena"])

    def test_busca_en_ingredientes(self):
        prohibidas, _ = etiquetas_prohibidas([], ["fresa"])
        alimentos = [{"nombre": "Yogurt", "nombre_usda": "Yogurt", "ingredientes": "milk, fresas, sugar", "etiquetas": set()}]
        _, excluidos = filtrar_alimentos(alimentos, prohibidas)
        self.assertEqual(len(excluidos), 1)


class TestPlanSemanal(unittest.TestCase):
    def setUp(self):
        self.parche = mock.patch.object(plan_semanal, "buscar_y_convertir", _buscar_falso)
        self.parche.start()

    def tearDown(self):
        self.parche.stop()

    def _plan(self, **extra):
        dias = {d: [{"nombre": "trabajo", "inicio": "09:00", "fin": "17:00"}] for d in ["lunes", "martes", "miercoles"]}
        datos = dict(edad=25, sexo="mujer", altura_cm=165, peso_kg=60, nivel_actividad="moderado",
                     objetivo="bajar", enfermedades=[], alergias=[], hora_despertar="07:00",
                     hora_dormir="23:00", num_comidas=4, actividades_por_dia=dias)
        datos.update(extra)
        return plan_semanal.generar_plan_semana(**datos)

    def test_variedad_y_precision(self):
        plan = self._plan()
        semana = plan["plan_semana"]
        for dia, comidas in semana.items():
            for c in comidas:
                objetivo = {n: c[n] for n in plan_semanal.NOMBRES_MACROS}
                self.assertLessEqual(plan_semanal._error_relativo_maximo(objetivo, c["macros_logrados"]), 0.10)
        lunes = [{a["nombre"] for a in c["alimentos"]} for c in semana["lunes"]]
        martes = [{a["nombre"] for a in c["alimentos"]} for c in semana["martes"]]
        self.assertNotEqual(lunes, martes, "el plan es idéntico entre días")
        self.assertNotEqual(lunes[0], lunes[1], "desayuno y comida usan los mismos alimentos")

    def test_alergia_excluye_almendras(self):
        plan = self._plan(alergias=["frutos_secos"])
        nombres = {a["nombre"] for c in plan["plan_semana"]["lunes"] for a in c["alimentos"]}
        self.assertNotIn("Almendras", nombres)
        self.assertNotIn("Crema de cacahuate", nombres)

    def test_aviso_sin_usda(self):
        plan = self._plan(alergias=["lacteos"], incluir_catalogo_usda=False)
        self.assertTrue(any("No se consultaron" in a for a in plan["avisos_seguridad"]))


class TestFormularioWeb(unittest.TestCase):
    BASE = dict(edad="25", peso="60", altura="165", sexo="mujer", actividad="moderado", objetivo="bajar",
                embarazo="no", trimestre="1", hora_despertar="07:00", hora_dormir="23:00", num_comidas="4",
                tiene_actividad_principal="si", act_inicio="09:00", act_fin="17:00", tiene_descanso="si",
                desc_inicio="13:00", desc_fin="13:30", hace_deporte="si", dep_inicio="18:30", dep_fin="19:30")

    def enviar(self, **cambios):
        datos = dict(self.BASE)
        datos.update(cambios)
        r = aplicacion.app.test_client().post("/predecir", data=datos)
        return r.status_code, r.get_data(as_text=True)

    def test_caso_normal(self):
        codigo, html = self.enviar()
        self.assertEqual(codigo, 200)
        self.assertIn("1554.3", html)
        self.assertIn("Miércoles", html)
        self.assertIn("Sábado", html)

    def test_errores_claros_sin_caerse(self):
        casos = {
            "num_comidas": ("abc", "3, 4 o 5"),
            "act_inicio": ("", "Inicio estudio/trabajo"),
            "edad": ("0", "La edad debe estar entre"),
            "peso": ("500", "El peso"),
            "objetivo": ("Bajar peso", "objetivo"),
            "hora_dormir": ("07:00", "igual"),
        }
        for campo, (valor, mensaje) in casos.items():
            codigo, html = self.enviar(**{campo: valor})
            self.assertEqual(codigo, 200, campo)
            self.assertIn("alert-error", html, campo)
            self.assertIn(mensaje, html, campo)

    def test_etiqueta_de_error_generica(self):
        _, html = self.enviar(edad="0")
        self.assertIn("Revisa tus datos:", html)


if __name__ == "__main__":
    unittest.main()
