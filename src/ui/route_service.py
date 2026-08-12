"""Puente entre la interfaz, el grafo y el agente de busqueda.

Este modulo NO importa Streamlit a proposito. Traduce lo que el usuario hace
sobre el mapa (dos coordenadas sueltas) a lo que el agente entiende (dos nodos
del grafo), y devuelve el mismo diccionario de resultado que ya usa el equipo.
Al no depender de la interfaz se puede probar con unittest sin levantar ningun
servidor, y la logica queda separada del dibujo.

Su otra responsabilidad es proteger a find_nearest_node. Esa funcion busca el
nodo mas cercano expandiendo anillos de celdas sin ningun limite: dentro del
mapa responde en 0.3 ms, pero a 1.35 grados del borde tarda 400 ms y a 3 grados
2.096 ms. Y no avisa, devuelve en silencio el nodo del borde del mapa y la
interfaz acabaria mostrando una ruta que empieza donde el usuario no pidio. Por
eso aqui se comprueba primero que el punto caiga dentro del area cubierta por
el grafo, y si no, ni siquiera se consulta.
"""

from collections import namedtuple

from src.nearest_node import find_nearest_node
from src.search.astar import astar
from src.search.route_result import build_failure_result
from src.search.ucs import ucs

MapBounds = namedtuple("MapBounds", "min_lat min_lon max_lat max_lon")

# Holgura en grados alrededor del area del grafo. Un clic sobre la acera de la
# ultima calle del mapa cae tecnicamente fuera de la caja, y rechazarlo seria
# molesto. 0.02 grados son unos 2.2 km, distancia a la que find_nearest_node
# sigue respondiendo en pocos milisegundos.
BOUNDS_MARGIN_DEG = 0.02

ALGORITHM_ASTAR = "A*"
ALGORITHM_UCS = "UCS"
AVAILABLE_ALGORITHMS = (ALGORITHM_ASTAR, ALGORITHM_UCS)

OUTSIDE_ORIGIN_MESSAGE = (
    "El punto de origen está fuera del área del mapa de Santo Domingo."
)
OUTSIDE_GOAL_MESSAGE = (
    "El punto de destino está fuera del área del mapa de Santo Domingo."
)


def unknown_algorithm_message(algorithm):
    """Mensaje para un algoritmo que no existe en el proyecto."""
    return f"Algoritmo no disponible: '{algorithm}'. Use 'A*' o 'UCS'."


def compute_map_bounds(coordinates, margin=BOUNDS_MARGIN_DEG):
    """Calcula la caja que envuelve a todos los nodos del grafo.

    Se deriva de las coordenadas reales en vez de escribirse a mano: si el
    equipo cambia el archivo OSM por otro recorte, los limites se ajustan solos
    y no queda una constante mintiendo en el codigo.
    """
    latitudes = [point[0] for point in coordinates.values()]
    longitudes = [point[1] for point in coordinates.values()]

    return MapBounds(
        min_lat=min(latitudes) - margin,
        min_lon=min(longitudes) - margin,
        max_lat=max(latitudes) + margin,
        max_lon=max(longitudes) + margin,
    )


def is_inside_bounds(latitude, longitude, bounds):
    """Indica si un punto cae dentro del area cubierta por el mapa."""
    return (
        bounds.min_lat <= latitude <= bounds.max_lat
        and bounds.min_lon <= longitude <= bounds.max_lon
    )


def run_algorithm(graph, coordinates, start, goal, mode, algorithm):
    """Llama al algoritmo elegido. Ambos devuelven el mismo diccionario."""
    if algorithm == ALGORITHM_UCS:
        return ucs(graph, start, goal, mode=mode)

    return astar(graph, coordinates, start, goal, mode=mode)


def find_route(
    graph,
    coordinates,
    origin,
    goal,
    bounds,
    mode="distance",
    algorithm=ALGORITHM_ASTAR,
):
    """Calcula la ruta entre dos coordenadas del mapa.

    origin y goal son pares (latitud, longitud) tal como los entrega el clic
    sobre el mapa. Devuelve el diccionario de resultado del agente, tambien
    cuando algo va mal: la interfaz solo tiene que mirar "success" y mostrar
    "message". Nunca lanza una excepcion.
    """
    if algorithm not in AVAILABLE_ALGORITHMS:
        return build_failure_result(
            unknown_algorithm_message(algorithm),
            algorithm,
            "none",
        )

    # Las dos comprobaciones van ANTES de tocar find_nearest_node: ese es el
    # punto de todo el guard.
    if not is_inside_bounds(origin[0], origin[1], bounds):
        return build_failure_result(OUTSIDE_ORIGIN_MESSAGE, algorithm, "none")

    if not is_inside_bounds(goal[0], goal[1], bounds):
        return build_failure_result(OUTSIDE_GOAL_MESSAGE, algorithm, "none")

    start_node = find_nearest_node(origin[0], origin[1], coordinates)
    goal_node = find_nearest_node(goal[0], goal[1], coordinates)

    return run_algorithm(graph, coordinates, start_node, goal_node, mode, algorithm)


def route_polyline(path, coordinates):
    """Convierte la lista de ids de nodo en coordenadas para dibujar la ruta."""
    return [coordinates[node] for node in path if node in coordinates]


def route_endpoints(path, coordinates):
    """Coordenadas reales de los nodos donde la ruta empieza y termina.

    No coinciden con donde el usuario hizo clic: el sistema engancha cada clic
    al nodo mas cercano de la red vial. Mostrar ambos puntos deja ver ese
    enganche, que es parte de como funciona el sistema.
    """
    if not path:
        return None, None

    return coordinates.get(path[0]), coordinates.get(path[-1])
