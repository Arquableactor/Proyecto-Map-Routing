import tempfile
import unittest
from pathlib import Path

from src.graph_builder import build_raw_graph
from src.nearest_node import find_nearest_node


MINI_OSM = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">

    <node id="1" lat="18.4800" lon="-69.9000" />
    <node id="2" lat="18.4805" lon="-69.9000" />
    <node id="3" lat="18.4810" lon="-69.9000" />
    <node id="4" lat="18.4815" lon="-69.9000" />
    <node id="5" lat="18.4820" lon="-69.9000" />

    <way id="100">
        <nd ref="1" />
        <nd ref="2" />

        <tag k="highway" v="residential" />
        <tag k="name" v="Calle Bidireccional" />
    </way>

    <way id="101">
        <nd ref="2" />
        <nd ref="3" />

        <tag k="highway" v="primary" />
        <tag k="name" v="Avenida Una Via" />
        <tag k="oneway" v="yes" />
    </way>

    <way id="102">
        <nd ref="3" />
        <nd ref="4" />

        <tag k="highway" v="secondary" />
        <tag k="name" v="Avenida con Velocidad" />
        <tag k="maxspeed" v="45" />
    </way>

    <way id="103">
        <nd ref="4" />
        <nd ref="5" />

        <tag k="highway" v="footway" />
        <tag k="name" v="Sendero Peatonal" />
    </way>

</osm>
"""


class GraphTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Crea un archivo OSM pequeño que será utilizado
        por todas las pruebas.
        """

        cls.temp_directory = tempfile.TemporaryDirectory()

        cls.osm_path = (
            Path(cls.temp_directory.name)
            / "mini_map.osm"
        )

        cls.osm_path.write_text(
            MINI_OSM,
            encoding="utf-8",
        )

        cls.graph, cls.coordinates = build_raw_graph(
            cls.osm_path
        )

    @classmethod
    def tearDownClass(cls):
        """
        Elimina el archivo temporal cuando terminan
        todas las pruebas.
        """

        cls.temp_directory.cleanup()

    def test_bidirectional_way(self):
        """
        La vía residencial entre 1 y 2 debe funcionar
        en ambos sentidos.
        """

        self.assertIn(2, self.graph[1])
        self.assertIn(1, self.graph[2])

    def test_oneway_has_no_reverse_edge(self):
        """
        La vía entre 2 y 3 tiene oneway=yes,
        por lo que solamente debe existir 2 -> 3.
        """

        self.assertIn(3, self.graph[2])
        self.assertNotIn(2, self.graph[3])

    def test_all_edges_have_positive_distance(self):
        """
        Ninguna arista del grafo puede tener
        una distancia menor o igual a cero.
        """

        for neighbors in self.graph.values():
            for edge in neighbors.values():
                self.assertGreater(
                    edge["distance_m"],
                    0,
                )

    def test_all_edge_nodes_have_coordinates(self):
        """
        Todo nodo que aparezca en una arista debe
        tener sus coordenadas disponibles.
        """

        for start_node, neighbors in self.graph.items():
            self.assertIn(
                start_node,
                self.coordinates,
            )

            for end_node in neighbors:
                self.assertIn(
                    end_node,
                    self.coordinates,
                )

    def test_footway_is_excluded(self):
        """
        El nodo 5 solamente pertenece a una vía footway,
        por lo que no debe formar parte del grafo vehicular.
        """

        self.assertNotIn(5, self.graph)
        self.assertNotIn(5, self.coordinates)

    def test_time_uses_maxspeed_and_default_speed(self):
        """
        Comprueba el cálculo del tiempo usando tanto
        la velocidad por defecto como maxspeed.
        """

        default_edge = self.graph[1][2]

        expected_default_time = (
            default_edge["distance_m"]
            / (30 / 3.6)
        )

        self.assertAlmostEqual(
            default_edge["time_s"],
            expected_default_time,
            places=6,
        )

        maxspeed_edge = self.graph[3][4]

        expected_maxspeed_time = (
            maxspeed_edge["distance_m"]
            / (45 / 3.6)
        )

        self.assertAlmostEqual(
            maxspeed_edge["time_s"],
            expected_maxspeed_time,
            places=6,
        )

    def test_find_nearest_node(self):
        """
        Una búsqueda realizada exactamente sobre
        las coordenadas del nodo 3 debe devolver 3.
        """

        nearest_node = find_nearest_node(
            18.4810,
            -69.9000,
            self.coordinates,
        )

        self.assertEqual(
            nearest_node,
            3,
        )


if __name__ == "__main__":
    unittest.main()