import math
from collections import defaultdict

from src.geo_utils import haversine_distance


# Cada celda de la rejilla mide aproximadamente 0.002 grados.
GRID_CELL_SIZE = 0.002


# Estas variables permiten reutilizar la rejilla cuando se hacen
# varias búsquedas sobre el mismo conjunto de coordenadas.
_cached_grid = None
_cached_coordinates_id = None
_cached_coordinates_size = None


def get_grid_cell(latitude, longitude):
    """
    Calcula la celda de la rejilla a la que pertenece
    una coordenada geográfica.
    """

    row = math.floor(latitude / GRID_CELL_SIZE)
    column = math.floor(longitude / GRID_CELL_SIZE)

    return row, column


def build_spatial_grid(coordinates):
    """
    Construye una rejilla espacial agrupando los nodos
    según su latitud y longitud.
    """

    grid = defaultdict(list)

    for node_id, (latitude, longitude) in coordinates.items():
        cell = get_grid_cell(
            latitude,
            longitude,
        )

        grid[cell].append(node_id)

    return dict(grid)


def get_spatial_grid(coordinates):
    """
    Obtiene la rejilla espacial.

    Si ya fue construida para el mismo diccionario de
    coordenadas, se reutiliza para evitar recorrer todos
    los nodos nuevamente.
    """

    global _cached_grid
    global _cached_coordinates_id
    global _cached_coordinates_size

    coordinates_id = id(coordinates)
    coordinates_size = len(coordinates)

    cache_is_valid = (
        _cached_grid is not None
        and _cached_coordinates_id == coordinates_id
        and _cached_coordinates_size == coordinates_size
    )

    if cache_is_valid:
        return _cached_grid

    _cached_grid = build_spatial_grid(coordinates)
    _cached_coordinates_id = coordinates_id
    _cached_coordinates_size = coordinates_size

    return _cached_grid


def get_ring_cells(center_cell, ring):
    """
    Devuelve las celdas que forman un anillo alrededor
    de la celda donde se encuentra el punto buscado.
    """

    center_row, center_column = center_cell

    if ring == 0:
        return [center_cell]

    cells = []

    min_row = center_row - ring
    max_row = center_row + ring
    min_column = center_column - ring
    max_column = center_column + ring

    # Parte superior e inferior del anillo
    for column in range(min_column, max_column + 1):
        cells.append((min_row, column))
        cells.append((max_row, column))

    # Laterales del anillo.
    # No incluimos las esquinas porque ya fueron agregadas arriba.
    for row in range(min_row + 1, max_row):
        cells.append((row, min_column))
        cells.append((row, max_column))

    return cells


def find_nearest_node(latitude, longitude, coordinates):
    """
    Busca el nodo más cercano a una latitud y longitud.

    La búsqueda comienza en la celda donde cae el punto
    y se expande por anillos. Cuando aparecen candidatos
    por primera vez, también se revisa el anillo siguiente
    antes de elegir el nodo más cercano.
    """

    if not coordinates:
        raise ValueError(
            "No hay coordenadas disponibles para buscar el nodo más cercano."
        )

    grid = get_spatial_grid(coordinates)

    center_cell = get_grid_cell(
        latitude,
        longitude,
    )

    candidate_nodes = []

    ring = 0
    first_candidate_ring = None

    while True:
        ring_cells = get_ring_cells(
            center_cell,
            ring,
        )

        for cell in ring_cells:
            nodes_in_cell = grid.get(cell, [])

            if nodes_in_cell:
                candidate_nodes.extend(nodes_in_cell)

        # Guardamos el primer anillo donde aparecieron candidatos
        if candidate_nodes and first_candidate_ring is None:
            first_candidate_ring = ring

        # El requisito pide revisar también el anillo siguiente
        # antes de tomar una decisión.
        if (
            first_candidate_ring is not None
            and ring >= first_candidate_ring + 1
        ):
            break

        ring += 1

    nearest_node = None
    nearest_distance = float("inf")

    for node_id in candidate_nodes:
        node_latitude, node_longitude = coordinates[node_id]

        distance = haversine_distance(
            latitude,
            longitude,
            node_latitude,
            node_longitude,
        )

        if distance < nearest_distance:
            nearest_distance = distance
            nearest_node = node_id

    return nearest_node