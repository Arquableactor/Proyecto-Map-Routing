"""Pruebas del puente entre la interfaz y el agente de busqueda.

La prueba que mas importa aqui no es que salga un mensaje bonito cuando el
usuario hace clic fuera del mapa, sino que en ese caso NO se llegue a llamar a
find_nearest_node. Esa funcion tarda hasta 2 segundos con un punto lejano y
ademas devuelve en silencio el nodo del borde del mapa, asi que el guard solo
sirve si corta antes. Se comprueba con un espia sobre la funcion real.
"""

import unittest
from unittest.mock import patch

from src.ui.route_service import (
    BOUNDS_MARGIN_DEG,
    OUTSIDE_GOAL_MESSAGE,
    OUTSIDE_ORIGIN_MESSAGE,
    compute_map_bounds,
    find_route,
    is_inside_bounds,
    route_endpoints,
    route_polyline,
)

# Se reutiliza el grafo de juguete del agente para no mantener dos copias.
from tests.test_search import RESULT_KEYS, TOY_COORDINATES, TOY_GRAPH

# Coordenadas de los nodos 1 y 3 del grafo de juguete, que tienen ruta entre si.
ORIGIN = (18.4800, -69.9300)
GOAL = (18.4800, -69.9220)

# Bien lejos del area del grafo: en pleno Atlántico.
FAR_AWAY = (18.4800, -66.5000)


class MapBoundsTests(unittest.TestCase):
    """Los limites del mapa se derivan de los datos, no se escriben a mano."""

    def test_los_limites_salen_de_las_coordenadas(self):
        """La caja envuelve a todos los nodos, mas el margen."""
        bounds = compute_map_bounds(TOY_COORDINATES)

        latitudes = [point[0] for point in TOY_COORDINATES.values()]
        longitudes = [point[1] for point in TOY_COORDINATES.values()]

        self.assertAlmostEqual(bounds.min_lat, min(latitudes) - BOUNDS_MARGIN_DEG)
        self.assertAlmostEqual(bounds.max_lat, max(latitudes) + BOUNDS_MARGIN_DEG)
        self.assertAlmostEqual(bounds.min_lon, min(longitudes) - BOUNDS_MARGIN_DEG)
        self.assertAlmostEqual(bounds.max_lon, max(longitudes) + BOUNDS_MARGIN_DEG)

    def test_todos_los_nodos_del_grafo_caen_dentro(self):
        """Ningun nodo real puede quedar fuera de su propia caja."""
        bounds = compute_map_bounds(TOY_COORDINATES)

        for node, (latitude, longitude) in TOY_COORDINATES.items():
            with self.subTest(nodo=node):
                self.assertTrue(is_inside_bounds(latitude, longitude, bounds))

    def test_un_punto_lejano_queda_fuera(self):
        """Un clic en el mar no pertenece al mapa."""
        bounds = compute_map_bounds(TOY_COORDINATES)

        self.assertFalse(is_inside_bounds(FAR_AWAY[0], FAR_AWAY[1], bounds))

    def test_el_margen_admite_el_borde(self):
        """Un punto justo al lado de la ultima calle sigue siendo valido.

        Sin margen, un clic sobre la acera de la calle mas exterior del mapa se
        rechazaria aunque exista una calle a diez metros.
        """
        bounds = compute_map_bounds(TOY_COORDINATES)
        latitudes = [point[0] for point in TOY_COORDINATES.values()]

        justo_afuera = max(latitudes) + BOUNDS_MARGIN_DEG / 2

        self.assertTrue(is_inside_bounds(justo_afuera, -69.9260, bounds))


class FindRouteTests(unittest.TestCase):
    """Comportamiento de find_route sobre el grafo de juguete."""

    def setUp(self):
        self.bounds = compute_map_bounds(TOY_COORDINATES)

    def test_una_ruta_valida_devuelve_el_contrato_completo(self):
        """El resultado es el mismo diccionario que entrega el agente."""
        result = find_route(TOY_GRAPH, TOY_COORDINATES, ORIGIN, GOAL, self.bounds)

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(set(result.keys()), RESULT_KEYS)
        self.assertEqual(result["algorithm"], "A*")
        self.assertGreater(result["distance_m"], 0)

    def test_un_origen_fuera_del_mapa_ni_siquiera_consulta_el_grafo(self):
        """El guard tiene que cortar ANTES de llamar a find_nearest_node.

        Es toda la razon de existir de la validación: esa función tarda hasta
        2 segundos con un punto lejano y devuelve el nodo del borde sin avisar.
        """
        with patch("src.ui.route_service.find_nearest_node") as spy:
            result = find_route(
                TOY_GRAPH,
                TOY_COORDINATES,
                FAR_AWAY,
                GOAL,
                self.bounds,
            )

        spy.assert_not_called()
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], OUTSIDE_ORIGIN_MESSAGE)
        self.assertEqual(result["path"], [])

    def test_un_destino_fuera_del_mapa_tambien_se_rechaza(self):
        """El mensaje distingue cual de los dos puntos esta mal."""
        with patch("src.ui.route_service.find_nearest_node") as spy:
            result = find_route(
                TOY_GRAPH,
                TOY_COORDINATES,
                ORIGIN,
                FAR_AWAY,
                self.bounds,
            )

        spy.assert_not_called()
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], OUTSIDE_GOAL_MESSAGE)

    def test_se_puede_elegir_entre_astar_y_ucs(self):
        """Los dos algoritmos son intercambiables y coinciden en el costo."""
        by_astar = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
            algorithm="A*",
        )
        by_ucs = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
            algorithm="UCS",
        )

        self.assertEqual(by_ucs["algorithm"], "UCS")
        self.assertAlmostEqual(by_astar["distance_m"], by_ucs["distance_m"])

    def test_los_dos_modos_dan_rutas_distintas(self):
        """Menor distancia y menor tiempo no son el mismo recorrido."""
        by_distance = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
            mode="distance",
        )
        by_time = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
            mode="time",
        )

        self.assertNotEqual(by_distance["path"], by_time["path"])
        self.assertLess(by_distance["distance_m"], by_time["distance_m"])
        self.assertLess(by_time["estimated_time_s"], by_distance["estimated_time_s"])

    def test_un_algoritmo_desconocido_no_lanza_excepcion(self):
        """Cualquier error llega como success=False con mensaje legible."""
        result = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
            algorithm="Dijkstra bidireccional",
        )

        self.assertFalse(result["success"])
        self.assertIn("Dijkstra bidireccional", result["message"])

    def test_un_modo_invalido_lo_reporta_el_agente(self):
        """La validacion del modo ya vive en el agente; no se duplica aqui."""
        result = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
            mode="dinero",
        )

        self.assertFalse(result["success"])
        self.assertIn("dinero", result["message"])


class RouteGeometryTests(unittest.TestCase):
    """Conversion de la ruta a algo que Folium pueda dibujar."""

    def setUp(self):
        self.bounds = compute_map_bounds(TOY_COORDINATES)
        self.result = find_route(
            TOY_GRAPH,
            TOY_COORDINATES,
            ORIGIN,
            GOAL,
            self.bounds,
        )

    def test_la_polilinea_tiene_un_punto_por_nodo(self):
        """Cada nodo de la ruta aporta una coordenada, en el mismo orden."""
        polyline = route_polyline(self.result["path"], TOY_COORDINATES)

        self.assertEqual(len(polyline), len(self.result["path"]))
        self.assertEqual(polyline[0], TOY_COORDINATES[self.result["path"][0]])
        self.assertEqual(polyline[-1], TOY_COORDINATES[self.result["path"][-1]])

    def test_los_extremos_son_los_nodos_enganchados(self):
        """Los extremos salen del grafo, no del clic del usuario."""
        start_point, goal_point = route_endpoints(
            self.result["path"],
            TOY_COORDINATES,
        )

        self.assertEqual(start_point, TOY_COORDINATES[self.result["path"][0]])
        self.assertEqual(goal_point, TOY_COORDINATES[self.result["path"][-1]])

    def test_una_ruta_vacia_no_revienta(self):
        """Cuando no hay ruta, la interfaz recibe estructuras vacias."""
        self.assertEqual(route_polyline([], TOY_COORDINATES), [])
        self.assertEqual(route_endpoints([], TOY_COORDINATES), (None, None))


if __name__ == "__main__":
    unittest.main()
