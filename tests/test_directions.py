"""Pruebas de las instrucciones paso a paso.

El grafo de juguete es una cruz de calles orientadas exactamente al norte, al
este y al oeste, para que los rumbos sean 0, 90 y 270 grados y los giros se
puedan comprobar a mano:

                    7  (18.4840)  vía sin nombre
                    |
                    6  (18.4830)  Prolongación Norte  (recto, cambia el nombre)
                    |
        5 --------- 3 --------- 4      (18.4820)
     Calle Oeste    |    Calle Este
                    2  (18.4810)  ^
                    |             |  Avenida Norte
                    1  (18.4800)  |

El tramo 1->2->3 son dos aristas de la misma calle: tienen que fundirse en un
solo tramo de 850 m. Desde el nodo 3 se puede girar a la derecha (Calle Este),
a la izquierda (Calle Oeste) o seguir recto con otro nombre.

El giro a la izquierda es el caso interesante: se llega con rumbo 0 y se sale
con rumbo 270. La resta cruda daria +270, que se leeria como un giro a la
derecha. Solo tras normalizar aparece el -90 que corresponde a la izquierda.
"""

import unittest

from src.engine.directions import (
    bearing_degrees,
    build_legs,
    generate_route_instructions,
    street_label,
    turn_angle,
    turn_phrase,
)
from src.search.ucs import ucs

NORTH = ("Avenida Norte", "residential", 10)
EAST = ("Calle Este", "secondary", 20)
WEST = ("Calle Oeste", "secondary", 30)
STRAIGHT_ON = ("Prolongación Norte", "residential", 40)
NAMELESS = ("(sin nombre)", "service", 50)


def make_edge(distance_m, street_data):
    """Arista con el mismo formato que entrega Deivy."""
    street, highway, way_id = street_data

    return {
        "distance_m": distance_m,
        # 30 km/h; el tiempo no interviene en las instrucciones, pero el
        # contrato lo exige.
        "time_s": distance_m / (30 / 3.6),
        "street": street,
        "highway": highway,
        "way_id": way_id,
    }


TOY_GRAPH = {
    1: {2: make_edge(400.0, NORTH)},
    2: {3: make_edge(450.0, NORTH)},
    3: {
        4: make_edge(1200.0, EAST),
        5: make_edge(600.0, WEST),
        6: make_edge(300.0, STRAIGHT_ON),
    },
    4: {},
    5: {},
    6: {7: make_edge(250.0, NAMELESS)},
    7: {},
}

TOY_COORDINATES = {
    1: (18.4800, -69.9300),
    2: (18.4810, -69.9300),
    3: (18.4820, -69.9300),
    4: (18.4820, -69.9290),
    5: (18.4820, -69.9310),
    6: (18.4830, -69.9300),
    7: (18.4840, -69.9300),
}


def route(start, goal):
    """Ruta calculada de verdad, para no fabricar resultados a mano."""
    return ucs(TOY_GRAPH, start, goal)


class BearingTests(unittest.TestCase):
    """El rumbo y la normalizacion del giro."""

    def test_los_rumbos_cardinales(self):
        """Norte 0, este 90, oeste 270."""
        self.assertAlmostEqual(
            bearing_degrees(TOY_COORDINATES[2], TOY_COORDINATES[3]), 0.0, places=2
        )
        self.assertAlmostEqual(
            bearing_degrees(TOY_COORDINATES[3], TOY_COORDINATES[4]), 90.0, places=2
        )
        self.assertAlmostEqual(
            bearing_degrees(TOY_COORDINATES[3], TOY_COORDINATES[5]), 270.0, places=2
        )

    def test_la_normalizacion_toma_el_giro_mas_corto(self):
        """Cruzar el norte no puede leerse como una vuelta entera.

        De rumbo 350 a rumbo 10 hay 20 grados a la derecha, aunque la resta
        cruda diga -340.
        """
        self.assertAlmostEqual(turn_angle(350.0, 10.0), 20.0)
        self.assertAlmostEqual(turn_angle(10.0, 350.0), -20.0)
        self.assertAlmostEqual(turn_angle(0.0, 90.0), 90.0)
        self.assertAlmostEqual(turn_angle(0.0, 270.0), -90.0)

    def test_las_frases_de_giro(self):
        """Cada franja de angulo tiene su frase."""
        self.assertEqual(turn_phrase(5.0), "Continúe recto")
        self.assertEqual(turn_phrase(-5.0), "Continúe recto")
        self.assertEqual(turn_phrase(30.0), "Gire levemente a la derecha")
        self.assertEqual(turn_phrase(-30.0), "Gire levemente a la izquierda")
        self.assertEqual(turn_phrase(90.0), "Gire a la derecha")
        self.assertEqual(turn_phrase(-90.0), "Gire a la izquierda")
        self.assertEqual(turn_phrase(170.0), "Gire completamente a la derecha")


class LegGroupingTests(unittest.TestCase):
    """Agrupacion de segmentos consecutivos de la misma calle."""

    def test_dos_aristas_de_la_misma_calle_forman_un_solo_tramo(self):
        """1->2 y 2->3 son Avenida Norte: un tramo de 850 m, no dos de 400."""
        legs = build_legs(route(1, 4)["path"], TOY_GRAPH)

        self.assertEqual(len(legs), 2)
        self.assertEqual(legs[0]["street"], "Avenida Norte")
        self.assertAlmostEqual(legs[0]["distance_m"], 850.0)
        self.assertEqual(legs[0]["nodes"], [1, 2, 3])
        self.assertEqual(legs[1]["street"], "Calle Este")
        self.assertAlmostEqual(legs[1]["distance_m"], 1200.0)

    def test_la_suma_de_los_tramos_es_la_distancia_de_la_ruta(self):
        """Agrupar no puede perder ni duplicar metros."""
        result = route(1, 4)
        legs = build_legs(result["path"], TOY_GRAPH)

        total = sum(leg["distance_m"] for leg in legs)

        self.assertAlmostEqual(total, result["distance_m"], places=2)


class InstructionTests(unittest.TestCase):
    """Las frases completas que ve el usuario."""

    def test_un_giro_a_la_derecha(self):
        """Se llega con rumbo norte y se sale al este."""
        result = route(1, 4)
        steps = generate_route_instructions(result, TOY_GRAPH, TOY_COORDINATES)

        self.assertEqual(
            steps,
            [
                "Inicie en Avenida Norte.",
                "Continúe durante 850 metros.",
                "Gire a la derecha hacia Calle Este.",
                "Continúe durante 1.2 kilómetros.",
                "Ha llegado a su destino.",
            ],
        )

    def test_un_giro_a_la_izquierda(self):
        """El caso que solo sale bien si el angulo esta normalizado."""
        result = route(1, 5)
        steps = generate_route_instructions(result, TOY_GRAPH, TOY_COORDINATES)

        self.assertIn("Gire a la izquierda hacia Calle Oeste.", steps)
        self.assertNotIn("Gire a la derecha hacia Calle Oeste.", steps)

    def test_seguir_recto_aunque_cambie_el_nombre(self):
        """Mismo rumbo y otro nombre: se avisa del cambio, no de un giro."""
        result = route(1, 6)
        steps = generate_route_instructions(result, TOY_GRAPH, TOY_COORDINATES)

        self.assertIn("Continúe recto hacia Prolongación Norte.", steps)

    def test_una_via_sin_nombre(self):
        """El marcador de OpenStreetMap no se le enseña al usuario."""
        result = route(6, 7)
        steps = generate_route_instructions(result, TOY_GRAPH, TOY_COORDINATES)

        self.assertEqual(
            steps,
            [
                "Inicie en una vía sin nombre.",
                "Continúe durante 250 metros.",
                "Ha llegado a su destino.",
            ],
        )
        self.assertEqual(street_label("(sin nombre)"), "una vía sin nombre")

    def test_una_ruta_de_un_solo_segmento(self):
        """Dos nodos y una arista: no hay giros que calcular, y no falla."""
        result = route(6, 7)
        steps = generate_route_instructions(result, TOY_GRAPH, TOY_COORDINATES)

        self.assertEqual(len(steps), 3)
        self.assertTrue(steps[0].startswith("Inicie en"))
        self.assertEqual(steps[-1], "Ha llegado a su destino.")

    def test_una_busqueda_fallida_no_produce_instrucciones(self):
        """Sin ruta no hay nada que indicar, y tampoco una excepcion."""
        failed = ucs(TOY_GRAPH, 4, 1)

        self.assertFalse(failed["success"])
        self.assertEqual(
            generate_route_instructions(failed, TOY_GRAPH, TOY_COORDINATES),
            [],
        )

    def test_las_distancias_usan_el_formato_compartido(self):
        """Metros por debajo del kilometro, kilometros con un decimal."""
        steps = generate_route_instructions(
            route(1, 4),
            TOY_GRAPH,
            TOY_COORDINATES,
        )

        self.assertIn("Continúe durante 850 metros.", steps)
        self.assertIn("Continúe durante 1.2 kilómetros.", steps)


if __name__ == "__main__":
    unittest.main()
