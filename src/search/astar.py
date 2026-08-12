"""Busqueda A* sobre el grafo vial dirigido.

A* es UCS con informacion del terreno. En vez de expandir el nodo de menor
costo acumulado, expande el de menor

    f(n) = g(n) + h(n)

donde g(n) es el costo real ya gastado desde el origen hasta n, y h(n) es la
estimacion de lo que falta desde n hasta el destino. Esa suma es la mejor
apuesta sobre el costo total de la ruta completa que pasa por n, asi que la
busqueda deja de crecer en circulo alrededor del origen y se estira hacia el
destino.

Con h(n) = 0 para todo n, A* se convierte exactamente en UCS. Los dos estan en
el proyecto para poder demostrar esa relacion con numeros medidos.
"""

import heapq
import time

from src.search.heuristics import (
    DEFAULT_MAX_SPEED_MPS,
    HEURISTIC_NAMES,
    distance_heuristic,
    time_heuristic,
)
from src.search.route_result import (
    INFINITE_COST,
    NO_HEURISTIC,
    NO_ROUTE_MESSAGE,
    build_failure_result,
    build_success_result,
    elapsed_ms,
    get_cost_key,
    reconstruct_path,
    validate_request,
)

ALGORITHM_NAME = "A*"


def make_heuristic(mode, goal, coordinates, max_speed_mps):
    """Devuelve la funcion h(n) que corresponde al modo de busqueda.

    El destino y las coordenadas quedan fijados de antemano para que dentro del
    bucle principal la llamada sea de un solo argumento.
    """
    if mode == "time":

        def heuristic(node):
            return time_heuristic(node, goal, coordinates, max_speed_mps)

        return heuristic

    def heuristic(node):
        return distance_heuristic(node, goal, coordinates)

    return heuristic


def astar(
    graph,
    coordinates,
    start,
    goal,
    mode="distance",
    max_speed_mps=DEFAULT_MAX_SPEED_MPS,
):
    """Busca la ruta optima entre start y goal usando A*.

    mode="distance" minimiza metros y usa la heuristica de linea recta.
    mode="time"     minimiza segundos y usa la linea recta dividida por la
                    velocidad maxima de la red.

    max_speed_mps solo interviene en modo tiempo. Debe ser mayor o igual que la
    velocidad de cualquier arista del grafo; si se queda corto, la heuristica
    sobreestima y la ruta devuelta puede no ser la optima.

    Devuelve el mismo diccionario que ucs(). Nunca lanza excepciones.
    """
    started_at = time.perf_counter()

    problem = validate_request(graph, start, goal, mode)
    if problem is not None:
        return build_failure_result(
            problem,
            ALGORITHM_NAME,
            HEURISTIC_NAMES.get(mode, NO_HEURISTIC),
            0,
            elapsed_ms(started_at),
        )

    cost_key = get_cost_key(mode)
    heuristic_name = HEURISTIC_NAMES[mode]
    heuristic = make_heuristic(mode, goal, coordinates, max_speed_mps)

    # g_score[n] = costo real acumulado desde el origen hasta n.
    g_score = {start: 0.0}

    came_from = {}
    closed_set = set()
    visited_nodes = 0

    # La cola ordena por f = g + h. Ojo: lo que se guarda aqui es f, no g; el
    # costo real acumulado se consulta siempre en g_score.
    open_heap = [(heuristic(start), start)]

    while open_heap:
        _current_f, current_node = heapq.heappop(open_heap)

        # Entrada obsoleta dejada por una reinsercion (lazy deletion).
        if current_node in closed_set:
            continue

        closed_set.add(current_node)
        visited_nodes += 1

        # Igual que en UCS: la meta se confirma al SACAR el nodo de la cola. Al
        # insertarlo, su costo todavia puede bajar por un camino mejor.
        if current_node == goal:
            path = reconstruct_path(came_from, start, goal)
            return build_success_result(
                graph,
                path,
                visited_nodes,
                elapsed_ms(started_at),
                ALGORITHM_NAME,
                heuristic_name,
            )

        # Se usa g_score y NO la prioridad recien sacada, porque esa incluye la
        # heuristica. Confundirlas es el error mas comun al escribir A*.
        current_cost = g_score[current_node]

        for neighbor, edge in graph.get(current_node, {}).items():
            if neighbor in closed_set:
                continue

            tentative_cost = current_cost + edge[cost_key]

            if tentative_cost < g_score.get(neighbor, INFINITE_COST):
                g_score[neighbor] = tentative_cost
                came_from[neighbor] = current_node
                heapq.heappush(
                    open_heap,
                    (tentative_cost + heuristic(neighbor), neighbor),
                )

    # La cola se vacio sin llegar al destino: no existe camino dirigido.
    return build_failure_result(
        NO_ROUTE_MESSAGE,
        ALGORITHM_NAME,
        heuristic_name,
        visited_nodes,
        elapsed_ms(started_at),
    )
