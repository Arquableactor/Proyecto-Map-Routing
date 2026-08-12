import xml.etree.ElementTree as ET


# Tipos de vías que vamos a permitir para el perfil de automóvil
ALLOWED_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service",
}


# Valores de acceso que hacen que una vía no sea utilizable
BLOCKED_ACCESS_VALUES = {
    "no",
    "private",
}


def get_way_tags(way_element):
    """
    Convierte las etiquetas de una vía OSM en un diccionario.
    """

    tags = {}

    for tag in way_element.findall("tag"):
        key = tag.get("k")
        value = tag.get("v")

        if key is not None and value is not None:
            tags[key] = value

    return tags


def is_drivable_way(tags):
    """
    Indica si una vía puede formar parte del grafo para vehículos.
    """

    highway = tags.get("highway")

    # Si no es uno de los tipos de carretera permitidos, no se utiliza
    if highway not in ALLOWED_HIGHWAYS:
        return False

    access = tags.get("access", "").lower()

    if access in BLOCKED_ACCESS_VALUES:
        return False

    motor_vehicle = tags.get("motor_vehicle", "").lower()

    if motor_vehicle == "no":
        return False

    return True


def parse_drivable_ways(osm_path):
    """
    Primera pasada sobre el archivo OSM.

    Busca las vías que pueden ser utilizadas por vehículos y guarda
    también los IDs de los nodos que aparecen en esas vías.
    """

    ways = []
    needed_node_ids = set()

    context = ET.iterparse(osm_path, events=("end",))

    for _, elem in context:

        # En esta primera pasada no necesitamos guardar los nodos
        # completos del mapa, solamente las vías.
        if elem.tag == "node":
            elem.clear()
            continue

        # Las relaciones de OpenStreetMap tampoco son necesarias
        # para construir nuestro grafo.
        if elem.tag == "relation":
            elem.clear()
            continue

        # No limpiamos aquí los elementos <nd> ni <tag>,
        # porque forman parte de una vía que todavía no ha terminado.
        if elem.tag != "way":
            continue

        tags = get_way_tags(elem)

        if is_drivable_way(tags):
            node_ids = []

            for node_ref in elem.findall("nd"):
                ref = node_ref.get("ref")

                if ref is not None:
                    node_ids.append(int(ref))

            # Una vía necesita al menos dos nodos para formar un segmento
            if len(node_ids) >= 2:
                way_id = elem.get("id")

                if way_id is not None:
                    way = {
                        "id": int(way_id),
                        "nodes": node_ids,
                        "tags": tags,
                    }

                    ways.append(way)
                    needed_node_ids.update(node_ids)

        # La vía ya fue procesada, así que podemos liberar su memoria
        elem.clear()

    return ways, needed_node_ids


def parse_needed_nodes(osm_path, needed_node_ids):
    """
    Segunda pasada sobre el archivo OSM.

    Guarda solamente las coordenadas de los nodos que pertenecen
    a las vías vehiculares encontradas en la primera pasada.
    """

    coordinates = {}

    context = ET.iterparse(osm_path, events=("end",))

    for _, elem in context:

        if elem.tag == "node":
            node_id_value = elem.get("id")

            if node_id_value is not None:
                node_id = int(node_id_value)

                if node_id in needed_node_ids:
                    latitude = elem.get("lat")
                    longitude = elem.get("lon")

                    if latitude is not None and longitude is not None:
                        coordinates[node_id] = (
                            float(latitude),
                            float(longitude),
                        )

            # Ya revisamos este nodo y podemos liberar su memoria
            elem.clear()

        elif elem.tag == "way":
            # En esta segunda pasada ya no necesitamos las vías
            elem.clear()

        elif elem.tag == "relation":
            elem.clear()

    return coordinates


def parse_osm(osm_path):
    """
    Ejecuta las dos pasadas necesarias sobre el archivo OSM.

    Devuelve:
        ways: vías vehiculares encontradas.
        coordinates: coordenadas de los nodos utilizados por esas vías.
    """

    ways, needed_node_ids = parse_drivable_ways(osm_path)

    coordinates = parse_needed_nodes(
        osm_path,
        needed_node_ids,
    )

    return ways, coordinates