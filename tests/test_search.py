"""Pruebas del agente de busqueda sobre un grafo de juguete.

El grafo se disena a mano para que las rutas optimas se puedan calcular sin
computadora y poder defenderlas frente al profesor. Su mapa es este:

        4 ---500m/25s--- 5          (Avenida Norte / Calle Enlace)
        |                |
     700m/35s         400m/20s
     (una via)           |
        |                |
        1 ---500m/60s--- 2 ---500m/60s--- 3      (Calle Sur)
         \\                                /
          `------ 2000m/200s (una via) --´       (Callejón Largo)

        6 ---600m/60s--> 5   (una via: a 6 no llega nadie)

Tres detalles estan puestos a proposito:

1. La arista directa 1->3 es la de menos saltos pero la mas cara: obliga a que
   el algoritmo optimice costo y no cantidad de aristas.
2. La ruta sur es la mas corta en metros y la ruta norte la mas rapida en
   segundos, asi que los dos modos deben devolver rutas distintas.
3. Las distancias declaradas son siempre mayores o iguales que la linea recta
   entre las coordenadas. Esto mantiene admisible la heuristica de A* sobre
   este mismo grafo: si se editan las distancias, hay que revisarlo.
"""

import unittest

from src.search.astar import astar
from src.search.heuristics import (
    distance_heuristic,
    graph_max_speed_mps,
    time_heuristic,
)
from src.search.route_result import (
    COST_KEYS,
    NO_ROUTE_MESSAGE,
    SAME_NODE_MESSAGE,
)
from src.search.ucs import ucs

# Claves exactas que Gabriel espera recibir.
RESULT_KEYS = {
    "success",
    "path",
    "distance_m",
    "estimated_time_s",
    "visited_nodes",
    "runtime_ms",
    "algorithm",
    "heuristic",
    "message",
}


def make_edge(distance_m, time_s, street, highway, way_id):
    """Crea una arista con el mismo formato que entrega Deivy."""
    return {
        "distance_m": distance_m,
        "time_s": time_s,
        "street": street,
        "highway": highway,
        "way_id": way_id,
    }


SOUTH = ("Calle Sur", "residential", 10)
NORTH = ("Avenida Norte", "primary", 20)
LINK = ("Calle Enlace", "secondary", 30)
ALLEY = ("Callejón Largo", "service", 40)
PRIVATE = ("Entrada Privada", "service", 50)

TOY_GRAPH = {
    1: {
        2: make_edge(500.0, 60.0, *SOUTH),
        4: make_edge(700.0, 35.0, *NORTH),
        3: make_edge(2000.0, 200.0, *ALLEY),
    },
    2: {
        1: make_edge(500.0, 60.0, *SOUTH),
        3: make_edge(500.0, 60.0, *SOUTH),
    },
    3: {
        2: make_edge(500.0, 60.0, *SOUTH),
        5: make_edge(400.0, 20.0, *LINK),
    },
    4: {
        5: make_edge(500.0, 25.0, *NORTH),
    },
    5: {
        4: make_edge(500.0, 25.0, *NORTH),
        3: make_edge(400.0, 20.0, *LINK),
    },
    6: {
        5: make_edge(600.0, 60.0, *PRIVATE),
    },
}

TOY_COORDINATES = {
    1: (18.4800, -69.9300),
    2: (18.4800, -69.9260),
    3: (18.4800, -69.9220),
    4: (18.4830, -69.9260),
    5: (18.4830, -69.9220),
    6: (18.4860, -69.9180),
}


class UcsTests(unittest.TestCase):
    """Comportamiento de Uniform Cost Search."""

    def assert_valid_path(self, graph, result):
        """Cada par consecutivo de la ruta debe existir como arista dirigida."""
        path = result["path"]

        for current_node, next_node in zip(path, path[1:]):
            self.assertIn(current_node, graph)
            self.assertIn(
                next_node,
                graph[current_node],
                f"La ruta usa una arista inexistente: {current_node} -> {next_node}",
            )

    def test_resultado_cumple_el_contrato(self):
        """El diccionario devuelto tiene exactamente las claves acordadas."""
        result = ucs(TOY_GRAPH, 1, 3)

        self.assertEqual(set(result.keys()), RESULT_KEYS)
        self.assertEqual(result["algorithm"], "UCS")
        self.assertEqual(result["heuristic"], "none")
        self.assertGreater(result["visited_nodes"], 0)
        self.assertGreaterEqual(result["runtime_ms"], 0.0)

    def test_optimiza_costo_y_no_cantidad_de_saltos(self):
        """La arista directa 1->3 es un solo salto pero cuesta el doble.

        Traza esperada: se expanden 1, 2, 4 y 3. El nodo 3 entra a la cola
        con costo 2000 en la primera expansion; si la meta se comprobara al
        insertar, la respuesta seria esa ruta cara. Como se comprueba al
        sacarlo, para entonces su costo ya bajo a 1000.
        """
        result = ucs(TOY_GRAPH, 1, 3, mode="distance")

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], [1, 2, 3])
        self.assertAlmostEqual(result["distance_m"], 1000.0)
        self.assertEqual(result["visited_nodes"], 4)
        self.assert_valid_path(TOY_GRAPH, result)

    def test_modo_tiempo_devuelve_otra_ruta(self):
        """La ruta norte es mas larga en metros pero llega antes."""
        shortest = ucs(TOY_GRAPH, 1, 3, mode="distance")
        fastest = ucs(TOY_GRAPH, 1, 3, mode="time")

        self.assertEqual(fastest["path"], [1, 4, 5, 3])
        self.assertAlmostEqual(fastest["estimated_time_s"], 80.0)
        self.assertAlmostEqual(fastest["distance_m"], 1600.0)

        # La ruta rapida recorre mas metros y la corta tarda mas segundos.
        self.assertGreater(fastest["distance_m"], shortest["distance_m"])
        self.assertLess(
            fastest["estimated_time_s"],
            shortest["estimated_time_s"],
        )

    def test_costo_total_coincide_con_la_suma_de_aristas(self):
        """Los totales reportados se recalculan aparte y deben coincidir."""
        for mode in COST_KEYS:
            with self.subTest(mode=mode):
                result = ucs(TOY_GRAPH, 1, 3, mode=mode)

                expected_distance = 0.0
                expected_time = 0.0

                for current_node, next_node in zip(
                    result["path"],
                    result["path"][1:],
                ):
                    edge = TOY_GRAPH[current_node][next_node]
                    expected_distance += edge["distance_m"]
                    expected_time += edge["time_s"]

                self.assertAlmostEqual(
                    result["distance_m"],
                    expected_distance,
                )
                self.assertAlmostEqual(
                    result["estimated_time_s"],
                    expected_time,
                )

    def test_respeta_las_vias_de_un_solo_sentido(self):
        """1->4 es una via de un sentido: volver obliga a dar la vuelta."""
        going = ucs(TOY_GRAPH, 1, 4, mode="distance")
        returning = ucs(TOY_GRAPH, 4, 1, mode="distance")

        self.assertEqual(going["path"], [1, 4])
        self.assertAlmostEqual(going["distance_m"], 700.0)

        self.assertEqual(returning["path"], [4, 5, 3, 2, 1])
        self.assertAlmostEqual(returning["distance_m"], 1900.0)

        # El grafo es dirigido: ir y volver no son simetricos.
        self.assertNotEqual(going["path"], list(reversed(returning["path"])))
        self.assert_valid_path(TOY_GRAPH, returning)

    def test_destino_inalcanzable(self):
        """A 6 no llega ninguna arista, aunque desde 6 si se pueda salir."""
        unreachable = ucs(TOY_GRAPH, 1, 6)

        self.assertFalse(unreachable["success"])
        self.assertEqual(unreachable["path"], [])
        self.assertEqual(unreachable["message"], NO_ROUTE_MESSAGE)

        # El sentido contrario si tiene ruta.
        reachable = ucs(TOY_GRAPH, 6, 1)

        self.assertTrue(reachable["success"])
        self.assertEqual(reachable["path"], [6, 5, 3, 2, 1])

    def test_origen_igual_a_destino(self):
        """Caso acordado con el equipo: se responde sin buscar."""
        result = ucs(TOY_GRAPH, 3, 3)

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], SAME_NODE_MESSAGE)

    def test_nodos_inexistentes(self):
        """Un id que no esta en el grafo no puede reventar la busqueda."""
        missing_start = ucs(TOY_GRAPH, 999, 3)
        missing_goal = ucs(TOY_GRAPH, 1, 999)

        self.assertFalse(missing_start["success"])
        self.assertFalse(missing_goal["success"])
        self.assertNotEqual(missing_start["message"], missing_goal["message"])

    def test_grafo_vacio_y_modo_invalido(self):
        """Entradas degeneradas: siempre success=False, nunca una excepcion."""
        empty = ucs({}, 1, 3)
        bad_mode = ucs(TOY_GRAPH, 1, 3, mode="dinero")

        self.assertFalse(empty["success"])
        self.assertFalse(bad_mode["success"])
        self.assertIn("dinero", bad_mode["message"])


class HeuristicTests(unittest.TestCase):
    """Propiedades matematicas de las que depende que A* sea optimo.

    Estas pruebas no comprueban "que el codigo corra": comprueban las dos
    condiciones que hacen valida la implementacion con closed_set.
    """

    def test_velocidad_maxima_del_grafo(self):
        """La via mas rapida del grafo de juguete es la Avenida Norte."""
        # 500 m en 25 s = 20 m/s = 72 km/h.
        self.assertAlmostEqual(graph_max_speed_mps(TOY_GRAPH), 20.0)

    def test_la_heuristica_nunca_sobreestima(self):
        """Admisibilidad: h(n) <= costo optimo real de n hasta el destino.

        El costo optimo real se obtiene con UCS, que no usa heuristica. Se
        comprueba desde todos los nodos que tienen ruta hasta el destino.
        """
        goal = 3
        toy_max_speed = graph_max_speed_mps(TOY_GRAPH)

        for node in TOY_GRAPH:
            if node == goal:
                continue

            with self.subTest(node=node):
                real_distance = ucs(TOY_GRAPH, node, goal, mode="distance")
                real_time = ucs(TOY_GRAPH, node, goal, mode="time")

                if not real_distance["success"]:
                    continue

                self.assertLessEqual(
                    distance_heuristic(node, goal, TOY_COORDINATES),
                    real_distance["distance_m"],
                    f"h1 sobreestima desde el nodo {node}",
                )
                self.assertLessEqual(
                    time_heuristic(node, goal, TOY_COORDINATES, toy_max_speed),
                    real_time["estimated_time_s"],
                    f"h2 sobreestima desde el nodo {node}",
                )

    def test_la_heuristica_es_consistente(self):
        """Consistencia: h(n) <= costo(n -> n') + h(n') en cada arista.

        Es la condicion que permite cerrar un nodo y no volver a mirarlo. Sin
        ella, A* con closed_set puede devolver rutas subóptimas aunque la
        heuristica sea admisible.
        """
        goal = 3
        toy_max_speed = graph_max_speed_mps(TOY_GRAPH)

        for current_node, neighbors in TOY_GRAPH.items():
            for next_node, edge in neighbors.items():
                with self.subTest(arista=(current_node, next_node)):
                    self.assertLessEqual(
                        distance_heuristic(current_node, goal, TOY_COORDINATES),
                        edge["distance_m"]
                        + distance_heuristic(next_node, goal, TOY_COORDINATES),
                    )
                    self.assertLessEqual(
                        time_heuristic(
                            current_node,
                            goal,
                            TOY_COORDINATES,
                            toy_max_speed,
                        ),
                        edge["time_s"]
                        + time_heuristic(
                            next_node,
                            goal,
                            TOY_COORDINATES,
                            toy_max_speed,
                        ),
                    )


class AstarTests(unittest.TestCase):
    """Comportamiento de A* y su relacion con UCS."""

    # Pares con ruta existente en el grafo de juguete.
    PAIRS = [(1, 3), (1, 4), (1, 5), (2, 4), (4, 1), (5, 1), (6, 1), (6, 3)]

    def test_resultado_cumple_el_contrato(self):
        """Mismas claves que UCS, con el nombre de la heuristica usada."""
        result = astar(TOY_GRAPH, TOY_COORDINATES, 1, 3)

        self.assertEqual(set(result.keys()), RESULT_KEYS)
        self.assertEqual(result["algorithm"], "A*")
        self.assertEqual(result["heuristic"], "distance")

        by_time = astar(TOY_GRAPH, TOY_COORDINATES, 1, 3, mode="time")
        self.assertEqual(by_time["heuristic"], "time")

    def test_mismo_costo_que_ucs(self):
        """La prueba central: A* es optimo, igual que UCS.

        Si algun par diera un costo distinto, la heuristica estaria
        sobreestimando o la condicion de parada estaria mal escrita.
        """
        toy_max_speed = graph_max_speed_mps(TOY_GRAPH)

        for start, goal in self.PAIRS:
            for mode in COST_KEYS:
                with self.subTest(par=(start, goal), mode=mode):
                    by_ucs = ucs(TOY_GRAPH, start, goal, mode=mode)
                    by_astar = astar(
                        TOY_GRAPH,
                        TOY_COORDINATES,
                        start,
                        goal,
                        mode=mode,
                        max_speed_mps=toy_max_speed,
                    )

                    self.assertTrue(by_ucs["success"])
                    self.assertTrue(by_astar["success"])

                    field = (
                        "estimated_time_s" if mode == "time" else "distance_m"
                    )
                    self.assertAlmostEqual(
                        by_astar[field],
                        by_ucs[field],
                        places=6,
                    )

    def test_expande_menos_nodos_que_ucs(self):
        """A* llega al mismo sitio mirando menos mapa."""
        toy_max_speed = graph_max_speed_mps(TOY_GRAPH)

        for mode in COST_KEYS:
            with self.subTest(mode=mode):
                by_ucs = ucs(TOY_GRAPH, 1, 3, mode=mode)
                by_astar = astar(
                    TOY_GRAPH,
                    TOY_COORDINATES,
                    1,
                    3,
                    mode=mode,
                    max_speed_mps=toy_max_speed,
                )

                self.assertLess(
                    by_astar["visited_nodes"],
                    by_ucs["visited_nodes"],
                )

    def test_heuristica_inadmisible_rompe_la_optimalidad(self):
        """Por que la velocidad maxima no se puede quedar corta.

        Con una velocidad maxima falsa de 2.5 m/s la heuristica de tiempo se
        infla, A* cree que rodear cuesta mucho mas de lo que cuesta y acaba
        devolviendo el atajo caro de 200 s en vez de la ruta buena de 80 s.

        El valor es exagerado a proposito para que el fallo se vea en un grafo
        de seis nodos. En el mapa real el mecanismo es el mismo cuando se
        declara VMAX = 80 km/h existiendo vias de 100.
        """
        correct = astar(
            TOY_GRAPH,
            TOY_COORDINATES,
            1,
            3,
            mode="time",
            max_speed_mps=graph_max_speed_mps(TOY_GRAPH),
        )
        broken = astar(
            TOY_GRAPH,
            TOY_COORDINATES,
            1,
            3,
            mode="time",
            max_speed_mps=2.5,
        )

        self.assertEqual(correct["path"], [1, 4, 5, 3])
        self.assertAlmostEqual(correct["estimated_time_s"], 80.0)

        # Misma implementacion y misma entrada: solo cambia la cota, y la ruta
        # que devuelve empeora.
        self.assertEqual(broken["path"], [1, 3])
        self.assertGreater(
            broken["estimated_time_s"],
            correct["estimated_time_s"],
        )

    def test_respeta_las_vias_de_un_solo_sentido(self):
        """Igual que UCS: el grafo dirigido manda."""
        going = astar(TOY_GRAPH, TOY_COORDINATES, 1, 4)
        returning = astar(TOY_GRAPH, TOY_COORDINATES, 4, 1)

        self.assertEqual(going["path"], [1, 4])
        self.assertEqual(returning["path"], [4, 5, 3, 2, 1])

    def test_casos_especiales(self):
        """Mismos errores controlados que UCS, nunca una excepcion."""
        unreachable = astar(TOY_GRAPH, TOY_COORDINATES, 1, 6)
        same_node = astar(TOY_GRAPH, TOY_COORDINATES, 3, 3)
        missing = astar(TOY_GRAPH, TOY_COORDINATES, 999, 3)
        empty = astar({}, TOY_COORDINATES, 1, 3)
        bad_mode = astar(TOY_GRAPH, TOY_COORDINATES, 1, 3, mode="dinero")

        self.assertFalse(unreachable["success"])
        self.assertEqual(unreachable["message"], NO_ROUTE_MESSAGE)
        self.assertFalse(same_node["success"])
        self.assertEqual(same_node["message"], SAME_NODE_MESSAGE)
        self.assertFalse(missing["success"])
        self.assertFalse(empty["success"])
        self.assertFalse(bad_mode["success"])

    def test_sin_coordenadas_sigue_siendo_correcto(self):
        """Sin coordenadas la heuristica vale 0 y A* degenera en UCS.

        Es una degradacion segura: pierde velocidad, no correccion.
        """
        without_coordinates = astar(TOY_GRAPH, {}, 1, 3)
        by_ucs = ucs(TOY_GRAPH, 1, 3)

        self.assertTrue(without_coordinates["success"])
        self.assertAlmostEqual(
            without_coordinates["distance_m"],
            by_ucs["distance_m"],
        )


if __name__ == "__main__":
    unittest.main()
