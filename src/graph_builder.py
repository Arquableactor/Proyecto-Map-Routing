import pickle
from collections import deque
from pathlib import Path

from src.geo_utils import haversine_distance
from src.osm_parser import parse_osm


# Velocidades utilizadas cuando la vía no tiene
# un maxspeed numérico definido en OpenStreetMap.
DEFAULT_SPEEDS = {
    "motorway": 80,
    "trunk": 70,
    "primary": 60,
    "secondary": 50,
    "tertiary": 40,
    "residential": 30,
    "unclassified": 30,
    "living_street": 20,
    "service": 20,
}


FORWARD_ONEWAY_VALUES = {
    "yes",
    "true",
    "1",
}


REVERSE_ONEWAY_VALUES = {
    "-1",
    "reverse",
}


def get_base_highway(highway):
    """
    Obtiene el tipo base de una vía.

    Ejemplos:
    primary_link -> primary
    motorway_link -> motorway
    """

    if highway.endswith("_link"):
        return highway[:-5]

    return highway


def get_speed_kmh(tags):
    """
    Obtiene la velocidad estimada de una vía en km/h.

    Si OpenStreetMap tiene un maxspeed numérico válido,
    se utiliza ese valor. Si no, se usa la velocidad
    por defecto según el tipo de vía.
    """

    maxspeed = tags.get("maxspeed")

    if maxspeed is not None:
        try:
            speed = float(maxspeed.strip())

            if speed > 0:
                return speed

        except ValueError:
            pass

    highway = tags.get("highway", "")
    base_highway = get_base_highway(highway)

    return DEFAULT_SPEEDS[base_highway]


def get_way_direction(tags):
    """
    Determina en qué sentido se puede recorrer una vía.
    """

    oneway = tags.get("oneway", "").strip().lower()

    if oneway in FORWARD_ONEWAY_VALUES:
        return "forward"

    if oneway in REVERSE_ONEWAY_VALUES:
        return "reverse"

    junction = tags.get("junction", "").strip().lower()

    if junction == "roundabout":
        return "forward"

    return "both"


def add_edge(
    graph,
    start_node,
    end_node,
    distance_m,
    time_s,
    street,
    highway,
    way_id,
):
    """
    Agrega una arista al grafo.

    Si ya existe una conexión entre los mismos nodos,
    se conserva la que tenga menor distancia.
    """

    if distance_m <= 0:
        return

    edge_data = {
        "distance_m": distance_m,
        "time_s": time_s,
        "street": street,
        "highway": highway,
        "way_id": way_id,
    }

    if start_node not in graph:
        graph[start_node] = {}

    if end_node not in graph:
        graph[end_node] = {}

    current_edge = graph[start_node].get(end_node)

    if current_edge is None:
        graph[start_node][end_node] = edge_data
        return

    if distance_m < current_edge["distance_m"]:
        graph[start_node][end_node] = edge_data


def build_raw_graph(osm_path):
    """
    Construye el grafo dirigido antes de eliminar
    las componentes pequeñas y aisladas.
    """

    ways, coordinates = parse_osm(osm_path)

    graph = {}

    for way in ways:
        way_id = way["id"]
        node_ids = way["nodes"]
        tags = way["tags"]

        highway = tags["highway"]
        street = tags.get("name", "(sin nombre)")

        speed_kmh = get_speed_kmh(tags)
        speed_mps = speed_kmh / 3.6

        direction = get_way_direction(tags)

        # Se trabaja solamente con pares de nodos consecutivos.
        for start_node, end_node in zip(node_ids, node_ids[1:]):

            if start_node not in coordinates:
                continue

            if end_node not in coordinates:
                continue

            start_lat, start_lon = coordinates[start_node]
            end_lat, end_lon = coordinates[end_node]

            distance_m = haversine_distance(
                start_lat,
                start_lon,
                end_lat,
                end_lon,
            )

            # No se permiten aristas con peso cero.
            if distance_m <= 0:
                continue

            time_s = distance_m / speed_mps

            if direction == "forward":
                add_edge(
                    graph,
                    start_node,
                    end_node,
                    distance_m,
                    time_s,
                    street,
                    highway,
                    way_id,
                )

            elif direction == "reverse":
                add_edge(
                    graph,
                    end_node,
                    start_node,
                    distance_m,
                    time_s,
                    street,
                    highway,
                    way_id,
                )

            else:
                add_edge(
                    graph,
                    start_node,
                    end_node,
                    distance_m,
                    time_s,
                    street,
                    highway,
                    way_id,
                )

                add_edge(
                    graph,
                    end_node,
                    start_node,
                    distance_m,
                    time_s,
                    street,
                    highway,
                    way_id,
                )

    return graph, coordinates


def build_undirected_neighbors(graph):
    """
    Crea una vista no dirigida del grafo.

    Esta estructura solamente se utiliza para encontrar
    las componentes conexas. No cambia la dirección real
    de las calles en el grafo original.
    """

    neighbors = {}

    for node in graph:
        neighbors[node] = set()

    for start_node, destinations in graph.items():
        for end_node in destinations:
            neighbors[start_node].add(end_node)
            neighbors[end_node].add(start_node)

    return neighbors


def find_component(start_node, neighbors, visited):
    """
    Recorre una componente conexa utilizando BFS iterativo.
    """

    component = set()
    queue = deque([start_node])

    visited.add(start_node)

    while queue:
        current_node = queue.popleft()
        component.add(current_node)

        for neighbor in neighbors[current_node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return component


def find_largest_component(graph):
    """
    Encuentra la componente conexa con mayor cantidad de nodos.
    """

    neighbors = build_undirected_neighbors(graph)

    visited = set()
    largest_component = set()

    for node in neighbors:
        if node in visited:
            continue

        component = find_component(
            node,
            neighbors,
            visited,
        )

        if len(component) > len(largest_component):
            largest_component = component

    return largest_component


def prune_to_largest_component(graph, coordinates):
    """
    Conserva solamente la componente conexa mayor
    y elimina los pequeños grupos de nodos aislados.
    """

    if not graph:
        stats = {
            "original_nodes": 0,
            "kept_nodes": 0,
            "removed_nodes": 0,
            "removed_percentage": 0.0,
        }

        return graph, coordinates, stats

    largest_component = find_largest_component(graph)

    original_nodes = len(graph)
    kept_nodes = len(largest_component)
    removed_nodes = original_nodes - kept_nodes

    removed_percentage = (
        removed_nodes / original_nodes
    ) * 100

    pruned_graph = {}

    for node in largest_component:
        pruned_graph[node] = {}

        for neighbor, edge_data in graph[node].items():
            if neighbor in largest_component:
                pruned_graph[node][neighbor] = edge_data

    pruned_coordinates = {}

    for node in largest_component:
        if node in coordinates:
            pruned_coordinates[node] = coordinates[node]

    stats = {
        "original_nodes": original_nodes,
        "kept_nodes": kept_nodes,
        "removed_nodes": removed_nodes,
        "removed_percentage": removed_percentage,
    }

    return pruned_graph, pruned_coordinates, stats


def get_cache_path(osm_path):
    """
    Devuelve la ruta donde se guardará el archivo de caché.
    """

    osm_path = Path(osm_path)

    return osm_path.parent / "graph_cache.pkl"


def save_graph_cache(cache_path, graph, coordinates):
    """
    Guarda el grafo y las coordenadas en un archivo pickle.
    """

    cache_data = {
        "graph": graph,
        "coordinates": coordinates,
    }

    with open(cache_path, "wb") as cache_file:
        pickle.dump(
            cache_data,
            cache_file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


def load_graph_cache(cache_path):
    """
    Carga el grafo y las coordenadas desde el archivo de caché.
    """

    with open(cache_path, "rb") as cache_file:
        cache_data = pickle.load(cache_file)

    graph = cache_data["graph"]
    coordinates = cache_data["coordinates"]

    return graph, coordinates


def build_graph(osm_path, profile="car"):
    """
    Construye o carga el grafo final utilizado por el sistema.

    Si existe graph_cache.pkl, se utiliza para evitar procesar
    nuevamente todo el archivo OSM.
    """

    if profile != "car":
        raise ValueError(
            f"Perfil no soportado: {profile}"
        )

    osm_path = Path(osm_path)
    cache_path = get_cache_path(osm_path)

    if cache_path.exists():
        try:
            graph, coordinates = load_graph_cache(
                cache_path
            )

            print(
                f"Grafo cargado desde caché: {cache_path}"
            )

            return graph, coordinates

        except (
            OSError,
            EOFError,
            pickle.PickleError,
            KeyError,
        ):
            print(
                "No se pudo utilizar la caché. "
                "El grafo será reconstruido."
            )

    print("Construyendo grafo desde el archivo OSM...")

    graph, coordinates = build_raw_graph(
        osm_path
    )

    graph, coordinates, stats = prune_to_largest_component(
        graph,
        coordinates,
    )

    print("Procesamiento del grafo terminado.")
    print(
        f"Nodos originales: "
        f"{stats['original_nodes']:,}"
    )
    print(
        f"Nodos conservados: "
        f"{stats['kept_nodes']:,}"
    )
    print(
        f"Nodos descartados: "
        f"{stats['removed_nodes']:,}"
    )
    print(
        "Porcentaje descartado: "
        f"{stats['removed_percentage']:.2f}%"
    )

    save_graph_cache(
        cache_path,
        graph,
        coordinates,
    )

    print(
        f"Caché guardada en: {cache_path}"
    )

    return graph, coordinates