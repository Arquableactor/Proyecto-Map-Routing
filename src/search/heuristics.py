"""Heuristicas admisibles para A* sobre el grafo vial.

Una heuristica h(n) estima lo que falta desde el nodo n hasta el destino. Para
que A* garantice la ruta optima, h nunca puede pasarse:

    h(n) <= costo real optimo desde n hasta el destino      (admisibilidad)

Las dos heuristicas de este modulo cumplen ademas la condicion mas fuerte de
consistencia:

    h(n) <= costo(n -> n') + h(n')   para toda arista n -> n'

que es la que justifica que A* pueda cerrar un nodo y no volver a revisarlo
nunca mas. Ambas se apoyan en el mismo hecho geometrico: la linea recta entre
dos puntos nunca es mas larga que el recorrido real por las calles.
"""

from src.geo_utils import haversine_distance

# Velocidad maxima presente en el grafo de Santo Domingo, medida sobre las
# aristas reales: 100 km/h en la Autopista Las Américas. Es el techo de toda la
# red, no el promedio.
#
# CUIDADO: este valor debe ser mayor o igual que la velocidad de CUALQUIER
# arista. Si se queda corto, la heuristica de tiempo sobreestima y A* deja de
# ser optimo: con una cota de 80 km/h, 16 de 343 pares probados devolvieron una
# ruta peor. Pasarse es seguro (solo la vuelve menos informada); quedarse corto
# es un error. Usa graph_max_speed_mps() para derivarlo del grafo cargado.
DEFAULT_MAX_SPEED_KMH = 100.0
DEFAULT_MAX_SPEED_MPS = DEFAULT_MAX_SPEED_KMH / 3.6

# Nombre que va al campo "heuristic" del resultado, segun el modo de busqueda.
HEURISTIC_NAMES = {
    "distance": "distance",
    "time": "time",
}


def straight_line_m(current_node, goal_node, coordinates):
    """Distancia en linea recta (haversine) entre dos nodos, en metros.

    Si algun nodo no tiene coordenadas se devuelve 0: es la estimacion mas
    conservadora posible, nunca sobreestima, y como maximo hace que A* explore
    de mas. Preferible a lanzar una excepcion en plena peticion del usuario.
    """
    current_point = coordinates.get(current_node)
    goal_point = coordinates.get(goal_node)

    if current_point is None or goal_point is None:
        return 0.0

    return haversine_distance(
        current_point[0],
        current_point[1],
        goal_point[0],
        goal_point[1],
    )


def distance_heuristic(current_node, goal_node, coordinates):
    """h1: metros en linea recta hasta el destino. Produce la ruta mas corta.

    Es admisible porque el costo de cada arista se mide en metros recorridos
    por la calle, y ninguna calle puede ser mas corta que la linea recta entre
    sus extremos. Como mucho la iguala, en una avenida perfectamente recta.
    """
    return straight_line_m(current_node, goal_node, coordinates)


def time_heuristic(
    current_node,
    goal_node,
    coordinates,
    max_speed_mps=DEFAULT_MAX_SPEED_MPS,
):
    """h2: segundos minimos imaginables hasta el destino. Ruta mas rapida.

    Se toma la linea recta al destino y se recorre a la velocidad maxima de
    toda la red. Ningun trayecto real puede ser mas rapido que eso: tendria que
    ir mas derecho que la linea recta o mas rapido que la via mas veloz del
    mapa. Por eso nunca sobreestima.
    """
    return straight_line_m(current_node, goal_node, coordinates) / max_speed_mps


def graph_max_speed_mps(graph):
    """Velocidad maxima real de las aristas del grafo, en m/s.

    Recorre el grafo completo una sola vez. Sirve para no depender de una
    constante acordada de palabra: si Deivy cambia su tabla de velocidades,
    este valor lo detecta y la heuristica sigue siendo admisible.
    """
    fastest_speed = 0.0

    for neighbors in graph.values():
        for edge in neighbors.values():
            edge_time = edge["time_s"]

            if edge_time > 0:
                speed = edge["distance_m"] / edge_time

                if speed > fastest_speed:
                    fastest_speed = speed

    return fastest_speed
