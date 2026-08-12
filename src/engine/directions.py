"""Instrucciones de navegacion paso a paso a partir de una ruta calculada.

El agente de busqueda devuelve una lista de identificadores de nodo. Eso le
sirve a la maquina, pero a una persona no le dice nada: nadie conduce mirando
"308757848, 308695340, 1867212443". Este modulo traduce esa lista a frases en
español.

El trabajo tiene dos partes:

1. AGRUPAR. Una avenida larga aparece en el grafo partida en decenas de aristas
   pequeñas, una entre cada esquina. Si se emitiera una instruccion por arista,
   saldrian cincuenta lineas diciendo "continúe" para una sola calle. Se juntan
   los segmentos consecutivos que comparten el mismo nombre de calle y se suman
   sus distancias: cada grupo es un tramo del recorrido.

2. DECIDIR EL GIRO. Entre un tramo y el siguiente hay que saber si el conductor
   dobla, y hacia donde. Se compara el rumbo con el que llega al final de un
   tramo contra el rumbo con el que sale al principio del siguiente.

El grafo se lee, nunca se modifica: @st.cache_resource comparte el mismo objeto
entre todas las sesiones, y anotar algo dentro contaminaria otras busquedas.
"""

import math

from src.ui.ui_helpers import format_distance

# Valor con el que Deivy marca las vias sin nombre en OpenStreetMap.
UNNAMED_STREET = "(sin nombre)"
UNNAMED_LABEL = "una vía sin nombre"

# Umbrales del giro, en grados absolutos.
STRAIGHT_DEGREES = 20.0
SLIGHT_DEGREES = 45.0
SHARP_DEGREES = 135.0

FULL_TURN = 360.0
HALF_TURN = 180.0


def bearing_degrees(origin, destination):
    """Rumbo inicial del trayecto entre dos coordenadas, en grados.

    El rumbo se mide desde el norte y en sentido horario: 0 es norte, 90 este,
    180 sur, 270 oeste. Es el angulo que marcaria una brujula al arrancar.

    No sirve la trigonometria plana porque la Tierra es una esfera y los
    meridianos convergen hacia los polos. La formula del rumbo inicial corrige
    esa convergencia multiplicando por el coseno de la latitud.
    """
    origin_lat = math.radians(origin[0])
    origin_lon = math.radians(origin[1])
    destination_lat = math.radians(destination[0])
    destination_lon = math.radians(destination[1])

    delta_lon = destination_lon - origin_lon

    east_component = math.sin(delta_lon) * math.cos(destination_lat)
    north_component = math.cos(origin_lat) * math.sin(destination_lat) - (
        math.sin(origin_lat) * math.cos(destination_lat) * math.cos(delta_lon)
    )

    # atan2 devuelve el angulo en el rango -180..180; el modulo lo lleva a
    # 0..360, que es como se leen los rumbos.
    return (math.degrees(math.atan2(east_component, north_component)) + FULL_TURN) % FULL_TURN


def turn_angle(incoming_bearing, outgoing_bearing):
    """Cuanto hay que girar para pasar de un rumbo al otro, en grados.

    Positivo es a la derecha y negativo a la izquierda.

    La normalizacion es imprescindible, no un detalle de estilo. Los rumbos
    viven en un circulo: si se llega con rumbo 350 y se sale con rumbo 10, la
    resta cruda da 10 - 350 = -340, que se leeria como un giro brutal a la
    izquierda cuando en realidad es un giro suave de 20 grados a la derecha.

    Sumar 180, tomar el modulo 360 y restar 180 lleva cualquier diferencia al
    rango -180..180, es decir, a la rotacion mas corta entre los dos rumbos,
    que es la que de verdad hace el conductor.
    """
    difference = outgoing_bearing - incoming_bearing

    return ((difference + HALF_TURN) % FULL_TURN) - HALF_TURN


def turn_phrase(angle):
    """Traduce el angulo de giro a la frase que se le dice al conductor."""
    magnitude = abs(angle)

    if magnitude < STRAIGHT_DEGREES:
        return "Continúe recto"

    side = "la derecha" if angle > 0 else "la izquierda"

    if magnitude < SLIGHT_DEGREES:
        return f"Gire levemente a {side}"

    if magnitude < SHARP_DEGREES:
        return f"Gire a {side}"

    return f"Gire completamente a {side}"


def street_label(street):
    """Nombre de la calle tal como se le muestra al usuario."""
    if not street or street == UNNAMED_STREET:
        return UNNAMED_LABEL

    return street


def build_legs(path, graph):
    """Agrupa la ruta en tramos de una sola calle.

    Devuelve una lista de diccionarios con el nombre de la calle, la distancia
    total del tramo y los nodos que lo componen. Los nodos hacen falta despues
    para calcular los rumbos de entrada y de salida.
    """
    legs = []

    for current_node, next_node in zip(path, path[1:]):
        edge = graph[current_node][next_node]
        street = edge["street"]

        if legs and legs[-1]["street"] == street:
            legs[-1]["distance_m"] += edge["distance_m"]
            legs[-1]["nodes"].append(next_node)
        else:
            legs.append(
                {
                    "street": street,
                    "distance_m": edge["distance_m"],
                    "nodes": [current_node, next_node],
                }
            )

    return legs


def leg_initial_bearing(leg, coordinates):
    """Rumbo del PRIMER segmento del tramo: con el que se entra en la calle."""
    return segment_bearing(leg["nodes"][0], leg["nodes"][1], coordinates)


def leg_final_bearing(leg, coordinates):
    """Rumbo del ULTIMO segmento del tramo: con el que se llega a la esquina.

    Se usa el ultimo segmento y no los extremos del tramo completo porque una
    calle curva daria un rumbo promedio que no corresponde a como se llega de
    verdad al cruce.
    """
    return segment_bearing(leg["nodes"][-2], leg["nodes"][-1], coordinates)


def segment_bearing(origin_node, destination_node, coordinates):
    """Rumbo entre dos nodos, o None si a alguno le faltan coordenadas."""
    origin = coordinates.get(origin_node)
    destination = coordinates.get(destination_node)

    if origin is None or destination is None:
        return None

    return bearing_degrees(origin, destination)


def transition_phrase(previous_leg, leg, coordinates):
    """Frase de giro entre dos tramos consecutivos."""
    incoming = leg_final_bearing(previous_leg, coordinates)
    outgoing = leg_initial_bearing(leg, coordinates)

    # Sin coordenadas no se puede saber el giro; se sigue sin inventarlo.
    if incoming is None or outgoing is None:
        return "Continúe"

    return turn_phrase(turn_angle(incoming, outgoing))


def generate_route_instructions(result, graph, coordinates):
    """Convierte el resultado del agente en instrucciones legibles en español.

    Devuelve una lista de frases. Si la busqueda fallo o la ruta no tiene al
    menos dos nodos, devuelve una lista vacia: la interfaz simplemente no
    muestra el bloque de indicaciones.
    """
    if not result.get("success"):
        return []

    path = result.get("path") or []

    if len(path) < 2:
        return []

    legs = build_legs(path, graph)

    if not legs:
        return []

    instructions = [f"Inicie en {street_label(legs[0]['street'])}."]
    instructions.append(f"Continúe durante {format_distance(legs[0]['distance_m'])}.")

    for previous_leg, leg in zip(legs, legs[1:]):
        phrase = transition_phrase(previous_leg, leg, coordinates)
        instructions.append(f"{phrase} hacia {street_label(leg['street'])}.")
        instructions.append(f"Continúe durante {format_distance(leg['distance_m'])}.")

    # No se dice de que lado queda el destino: el sistema engancha el destino a
    # un nodo de la propia calle, asi que no hay un lado que calcular sin
    # inventarselo.
    instructions.append("Ha llegado a su destino.")

    return instructions
