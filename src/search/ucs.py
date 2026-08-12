"""Uniform Cost Search (UCS), equivalente a Dijkstra con prueba de meta.

Idea del algoritmo: mantener una frontera de nodos por explorar y expandir
siempre el de menor costo acumulado g(n) desde el origen. Como ningun peso del
grafo es negativo, cuando un nodo sale de la cola su costo ya no puede mejorar,
y por eso la primera ruta completa que encuentra es la mas barata.

UCS es la linea base del proyecto: A* debe llegar al mismo costo total pero
expandiendo menos nodos. Si alguna vez difieren, el problema esta en la
heuristica de A*, no aqui.
"""

import heapq
import time

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

ALGORITHM_NAME = "UCS"


def ucs(graph, start, goal, mode="distance"):
    """Busca la ruta de menor costo entre start y goal.

    mode="distance" minimiza metros recorridos (ruta mas corta).
    mode="time"     minimiza segundos estimados (ruta mas rapida).

    Devuelve el diccionario de resultado descrito en route_result.py. Nunca
    lanza una excepcion: los casos imposibles vuelven con success=False.
    """
    started_at = time.perf_counter()

    problem = validate_request(graph, start, goal, mode)
    if problem is not None:
        return build_failure_result(
            problem,
            ALGORITHM_NAME,
            NO_HEURISTIC,
            0,
            elapsed_ms(started_at),
        )

    cost_key = get_cost_key(mode)

    # g_score[n] = mejor costo conocido para llegar desde el origen hasta n.
    g_score = {start: 0.0}

    # came_from[n] = nodo anterior a n en el mejor camino conocido.
    came_from = {}

    # Nodos ya expandidos: su costo definitivo ya fue confirmado.
    closed_set = set()

    visited_nodes = 0

    # La cola de prioridad guarda (costo_acumulado, nodo). heapq ordena por el
    # primer elemento y desempata con el id del nodo, que es un entero: el
    # recorrido queda determinista y nunca falla al comparar.
    open_heap = [(0.0, start)]

    while open_heap:
        current_cost, current_node = heapq.heappop(open_heap)

        # heapq no permite bajar la prioridad de una entrada ya insertada, asi
        # que cuando encontramos un camino mejor insertamos el nodo otra vez.
        # Las entradas viejas quedan en la cola y se descartan aqui.
        if current_node in closed_set:
            continue

        closed_set.add(current_node)
        visited_nodes += 1

        # La meta se comprueba al SACAR el nodo de la cola, no al insertarlo.
        # Al insertarlo su costo todavia puede mejorar mas adelante, y cortar
        # ahi devolveria una ruta subóptima.
        if current_node == goal:
            path = reconstruct_path(came_from, start, goal)
            return build_success_result(
                graph,
                path,
                visited_nodes,
                elapsed_ms(started_at),
                ALGORITHM_NAME,
                NO_HEURISTIC,
            )

        # graph.get() protege contra nodos que aparecen como destino de una
        # arista pero no tienen entrada propia en el grafo.
        for neighbor, edge in graph.get(current_node, {}).items():
            if neighbor in closed_set:
                continue

            tentative_cost = current_cost + edge[cost_key]

            if tentative_cost < g_score.get(neighbor, INFINITE_COST):
                g_score[neighbor] = tentative_cost
                came_from[neighbor] = current_node
                heapq.heappush(open_heap, (tentative_cost, neighbor))

    # La cola se vacio sin llegar al destino: no existe camino dirigido.
    return build_failure_result(
        NO_ROUTE_MESSAGE,
        ALGORITHM_NAME,
        NO_HEURISTIC,
        visited_nodes,
        elapsed_ms(started_at),
    )
