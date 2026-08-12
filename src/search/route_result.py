"""Contrato de salida del agente de busqueda y validaciones comunes.

Todo algoritmo de este paquete (UCS, A*) devuelve exactamente el mismo
diccionario. Ese formato esta acordado con Gabriel, que dibuja la ruta
en el mapa: cambiar una clave rompe la integracion, asi que no se toca sin
avisar al equipo.

Aqui viven tambien las piezas que UCS y A* comparten, para que ambos midan y
reporten igual y la tabla comparativa del informe sea justa.
"""

import math
import time

# Cada modo de busqueda optimiza una magnitud distinta de la misma arista.
COST_KEYS = {
    "distance": "distance_m",
    "time": "time_s",
}

# Valor del campo "heuristic" cuando el algoritmo no usa ninguna (UCS).
NO_HEURISTIC = "none"

EMPTY_GRAPH_MESSAGE = "El grafo está vacío."
MISSING_START_MESSAGE = "El nodo de origen no existe en el grafo."
MISSING_GOAL_MESSAGE = "El nodo de destino no existe en el grafo."
SAME_NODE_MESSAGE = "El origen y el destino son el mismo punto."
NO_ROUTE_MESSAGE = "No se encontró una ruta entre los puntos seleccionados."
SUCCESS_MESSAGE = "Ruta encontrada."


def get_cost_key(mode):
    """Traduce el modo de busqueda a la clave de costo de la arista.

    Devuelve None si el modo no es valido, para que quien llame lo reporte
    como error controlado en vez de reventar con un KeyError.
    """
    return COST_KEYS.get(mode)


def invalid_mode_message(mode):
    """Mensaje de error para un modo de busqueda desconocido."""
    return f"Modo de búsqueda no válido: '{mode}'. Use 'distance' o 'time'."


def validate_request(graph, start, goal, mode):
    """Revisa los casos especiales antes de empezar a buscar.

    Devuelve el mensaje del problema encontrado, o None si la peticion es
    valida. Se comprueba todo aqui para que ningun algoritmo lance excepciones
    hacia la API: el usuario puede hacer clic en cualquier parte del mapa.
    """
    if not graph:
        return EMPTY_GRAPH_MESSAGE

    if get_cost_key(mode) is None:
        return invalid_mode_message(mode)

    if start not in graph:
        return MISSING_START_MESSAGE

    if goal not in graph:
        return MISSING_GOAL_MESSAGE

    if start == goal:
        return SAME_NODE_MESSAGE

    return None


def elapsed_ms(started_at):
    """Milisegundos transcurridos desde una marca de time.perf_counter()."""
    return round((time.perf_counter() - started_at) * 1000.0, 3)


def reconstruct_path(came_from, start, goal):
    """Rehace la ruta caminando hacia atras desde el destino hasta el origen.

    came_from[n] guarda de que nodo se llego a n por el mejor camino conocido.
    El recorrido es iterativo, sin recursion: una ruta sobre el grafo real
    puede tener miles de nodos y agotaria la pila de Python.
    """
    path = [goal]
    current_node = goal

    while current_node != start:
        current_node = came_from[current_node]
        path.append(current_node)

    path.reverse()
    return path


def sum_path_costs(graph, path):
    """Suma la distancia y el tiempo reales de las aristas que forman la ruta.

    Se calculan siempre las dos magnitudes, sin importar cual se optimizo: el
    costo que reporta la busqueda es el de un solo modo, pero la interfaz
    necesita mostrar los kilometros y los minutos del recorrido completo.
    """
    total_distance = 0.0
    total_time = 0.0

    for current_node, next_node in zip(path, path[1:]):
        edge = graph[current_node][next_node]
        total_distance += edge["distance_m"]
        total_time += edge["time_s"]

    return total_distance, total_time


def build_success_result(
    graph,
    path,
    visited_nodes,
    runtime_ms,
    algorithm,
    heuristic,
):
    """Arma el resultado de una busqueda que si encontro ruta."""
    total_distance, total_time = sum_path_costs(graph, path)

    return {
        "success": True,
        "path": path,
        "distance_m": round(total_distance, 2),
        "estimated_time_s": round(total_time, 2),
        "visited_nodes": visited_nodes,
        "runtime_ms": runtime_ms,
        "algorithm": algorithm,
        "heuristic": heuristic,
        "message": SUCCESS_MESSAGE,
    }


def build_failure_result(
    message,
    algorithm,
    heuristic,
    visited_nodes=0,
    runtime_ms=0.0,
):
    """Arma el resultado de una busqueda sin ruta o con datos invalidos.

    Mantiene todas las claves del contrato: Gabriel siempre recibe la
    misma estructura y solo tiene que mirar "success".
    """
    return {
        "success": False,
        "path": [],
        "distance_m": 0.0,
        "estimated_time_s": 0.0,
        "visited_nodes": visited_nodes,
        "runtime_ms": runtime_ms,
        "algorithm": algorithm,
        "heuristic": heuristic,
        "message": message,
    }


# Costo infinito para nodos que todavia no tienen ningun camino conocido.
INFINITE_COST = math.inf
