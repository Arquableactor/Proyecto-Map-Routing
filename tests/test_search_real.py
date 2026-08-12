"""Verificacion del agente de busqueda sobre el grafo real de Santo Domingo.

El grafo de juguete de test_search.py demuestra que los algoritmos son
correctos en un caso que se puede calcular a mano. Este archivo comprueba lo
mismo donde de verdad importa: 156,000 nodos, calles de un solo sentido y
velocidades reales.

La prueba central es la igualdad de costo entre A* y UCS. UCS no usa
heuristica, asi que su resultado es el optimo por definicion; si A* devuelve
exactamente lo mismo explorando menos nodos, la heuristica no sobreestima. Es
la evidencia de admisibilidad sobre datos reales, y la primera pregunta de una
defensa oral.

Estas pruebas necesitan data/santo_domingo.osm, que no esta en el repositorio
por su tamano. Cuando falta, la clase entera se salta sola en vez de fallar,
para que la suite siga verde en una maquina recien clonada.
"""

import unittest
from pathlib import Path

from src.graph_builder import build_graph
from src.nearest_node import find_nearest_node
from src.search.astar import astar
from src.search.heuristics import DEFAULT_MAX_SPEED_MPS, graph_max_speed_mps
from src.search.metrics import SCENARIOS
from src.search.ucs import ucs

REPO_ROOT = Path(__file__).resolve().parents[1]
OSM_PATH = REPO_ROOT / "data" / "santo_domingo.osm"

# Tolerancia en metros y en segundos. Dos rutas igual de optimas pueden sumar
# sus aristas en distinto orden y diferir en el ultimo decimal.
COST_TOLERANCE = 0.01

# Margen relativo para comparar la cota de velocidad. El grafo guarda el tiempo
# como distancia/(km_h/3.6), y al recuperar la velocidad con distancia/tiempo el
# flotante no vuelve exactamente al mismo bit: sobra 1 ULP (3.5e-15 m/s). Este
# margen ignora ese ruido y sigue detectando un error de verdad, como declarar
# 80 km/h en una red que llega a 100.
SPEED_TOLERANCE = 1e-9

MODES = (("distance", "distance_m"), ("time", "estimated_time_s"))


@unittest.skipUnless(
    OSM_PATH.exists(),
    f"falta {OSM_PATH.relative_to(REPO_ROOT)}; se omiten las pruebas del mapa real",
)
class RealGraphSearchTests(unittest.TestCase):
    """Compara A* contra UCS en los mismos escenarios que reporta el informe."""

    @classmethod
    def setUpClass(cls):
        """Construye el grafo una sola vez para toda la clase."""
        cls.graph, cls.coordinates = build_graph(str(OSM_PATH))
        cls.max_speed_mps = graph_max_speed_mps(cls.graph)

        # Los escenarios se toman de metrics.py para que la tabla del informe y
        # estas pruebas no puedan separarse.
        cls.routable = [s for s in SCENARIOS if not s.get("expect_no_route")]
        cls.unroutable = [s for s in SCENARIOS if s.get("expect_no_route")]

    def snap(self, scenario):
        """Traduce las coordenadas del escenario a nodos del grafo."""
        start = find_nearest_node(
            scenario["origin"][0],
            scenario["origin"][1],
            self.coordinates,
        )
        goal = find_nearest_node(
            scenario["goal"][0],
            scenario["goal"][1],
            self.coordinates,
        )
        return start, goal

    def test_la_cota_de_velocidad_no_se_queda_corta(self):
        """La constante por defecto debe cubrir la via mas rapida del mapa.

        Si el grafo trae una arista mas rapida que DEFAULT_MAX_SPEED_MPS, la
        heuristica de tiempo sobreestima y A* pierde la optimalidad. Ya paso:
        con una cota de 80 km/h existiendo vias de 100, 16 de 343 pares
        probados devolvieron una ruta peor.
        """
        self.assertGreaterEqual(
            DEFAULT_MAX_SPEED_MPS,
            self.max_speed_mps * (1 - SPEED_TOLERANCE),
            "la velocidad maxima del grafo supera la cota de la heuristica",
        )

    def test_astar_iguala_el_costo_de_ucs(self):
        """Admisibilidad sobre el mapa real: A* no pierde ni un metro.

        Es la prueba de fondo del componente. Un fallo aqui significa que la
        heuristica sobreestima o que la condicion de parada esta mal.

        A* se llama SIN pasarle max_speed_mps, a proposito: asi se ejerce la
        constante por defecto, que es la que usara la interfaz. De nada sirve
        verificar una cota derivada del grafo si en produccion se usa otra.
        """
        for scenario in self.routable:
            start, goal = self.snap(scenario)

            for mode, field in MODES:
                with self.subTest(escenario=scenario["name"], modo=mode):
                    by_ucs = ucs(self.graph, start, goal, mode=mode)
                    by_astar = astar(
                        self.graph,
                        self.coordinates,
                        start,
                        goal,
                        mode=mode,
                    )

                    self.assertTrue(by_ucs["success"], by_ucs["message"])
                    self.assertTrue(by_astar["success"], by_astar["message"])
                    self.assertAlmostEqual(
                        by_astar[field],
                        by_ucs[field],
                        delta=COST_TOLERANCE,
                        msg="A* no devolvio el costo optimo",
                    )

    def test_astar_no_explora_mas_que_ucs(self):
        """La heuristica debe guiar, no estorbar."""
        for scenario in self.routable:
            start, goal = self.snap(scenario)

            for mode, _field in MODES:
                with self.subTest(escenario=scenario["name"], modo=mode):
                    by_ucs = ucs(self.graph, start, goal, mode=mode)
                    by_astar = astar(
                        self.graph,
                        self.coordinates,
                        start,
                        goal,
                        mode=mode,
                    )

                    self.assertLessEqual(
                        by_astar["visited_nodes"],
                        by_ucs["visited_nodes"],
                    )

    def test_la_ruta_devuelta_existe_en_el_grafo(self):
        """Cada par consecutivo de la ruta tiene que ser una arista dirigida.

        Comprueba de paso que se respetan las calles de un solo sentido: una
        arista al reves simplemente no existe en el diccionario.
        """
        for scenario in self.routable:
            start, goal = self.snap(scenario)

            with self.subTest(escenario=scenario["name"]):
                result = astar(
                    self.graph,
                    self.coordinates,
                    start,
                    goal,
                )
                path = result["path"]

                self.assertEqual(path[0], start)
                self.assertEqual(path[-1], goal)

                for current_node, next_node in zip(path, path[1:]):
                    self.assertIn(next_node, self.graph[current_node])

    def test_el_costo_coincide_con_la_suma_de_la_ruta(self):
        """El total reportado debe salir de las aristas realmente recorridas."""
        scenario = self.routable[1]
        start, goal = self.snap(scenario)

        result = astar(
            self.graph,
            self.coordinates,
            start,
            goal,
        )

        total_distance = 0.0
        total_time = 0.0

        for current_node, next_node in zip(result["path"], result["path"][1:]):
            edge = self.graph[current_node][next_node]
            total_distance += edge["distance_m"]
            total_time += edge["time_s"]

        self.assertAlmostEqual(result["distance_m"], total_distance, delta=COST_TOLERANCE)
        self.assertAlmostEqual(
            result["estimated_time_s"],
            total_time,
            delta=COST_TOLERANCE,
        )

    def test_destino_inalcanzable_no_lanza_excepcion(self):
        """Con 28,000 calles de un solo sentido, el caso sin ruta es real."""
        for scenario in self.unroutable:
            start, goal = self.snap(scenario)

            for mode, _field in MODES:
                with self.subTest(escenario=scenario["name"], modo=mode):
                    by_ucs = ucs(self.graph, start, goal, mode=mode)
                    by_astar = astar(
                        self.graph,
                        self.coordinates,
                        start,
                        goal,
                        mode=mode,
                    )

                    self.assertFalse(by_ucs["success"])
                    self.assertFalse(by_astar["success"])
                    self.assertEqual(by_astar["path"], [])
                    self.assertTrue(by_astar["message"])


if __name__ == "__main__":
    unittest.main()
