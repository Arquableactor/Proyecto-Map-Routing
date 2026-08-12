"""Interfaz web del sistema de ruteo sobre el mapa de Santo Domingo.

Streamlit vuelve a ejecutar este archivo COMPLETO cada vez que el usuario
interactua con cualquier control. Eso obliga a dos decisiones que estructuran
todo el archivo:

1. El grafo se carga con @st.cache_resource. Sin esa cache, cada clic
   reconstruiria 156.431 nodos y 328.071 aristas y la aplicacion seria
   inusable.
2. Lo que el usuario lleva seleccionado vive en st.session_state, nunca en
   variables normales: una variable global se reinicializaria en cada
   re-ejecucion y los puntos elegidos desaparecerian.

El calculo de la ruta no vive aqui: esta en src/ui/route_service.py, que no
depende de Streamlit y por eso se puede probar sin levantar un servidor.

Ejecutar con:
    streamlit run app.py
"""

from collections import namedtuple
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

from src.engine.directions import generate_route_instructions
from src.graph_builder import build_graph
from src.ui.route_service import (
    AVAILABLE_ALGORITHMS,
    compute_map_bounds,
    find_route,
    route_endpoints,
    route_polyline,
)
from src.ui.ui_helpers import (
    format_count,
    format_distance,
    format_duration,
    format_point,
)

OSM_PATH = Path("data/santo_domingo.osm")

# Centro y zoom elegidos a partir de la caja real del grafo,
# lat 18.390-18.653 y lon -70.169 a -69.693.
MAP_CENTER = (18.48, -69.93)
MAP_ZOOM = 12
MAP_HEIGHT = 560

ROUTE_COLOR = "#1D4ED8"

# Lo que ve el usuario, y el modo que entiende el agente.
SEARCH_MODES = {
    "Menor distancia": "distance",
    "Menor tiempo estimado": "time",
}

# Lugares con ruta ya verificada sobre el grafo. Son el respaldo de la
# demostracion: si los clics fallan, desde aqui se arma una ruta conocida.
KNOWN_PLACES = {
    "Museo de la Resistencia": (18.47177, -69.88757),
    "Centro Comercial Colón": (18.47394, -69.88385),
    "Sala Carlos Piantini": (18.47086, -69.91117),
    "Plaza Juan Barón": (18.46475, -69.89267),
    "Plaza Madelta III": (18.45838, -69.93866),
    "CEDIMAT": (18.48882, -69.92317),
}

RoadNetwork = namedtuple("RoadNetwork", "graph coordinates edge_count bounds")


@st.cache_resource(show_spinner="Construyendo el grafo vial de Santo Domingo…")
def load_road_network():
    """Carga el grafo una sola vez y lo reutiliza en toda la sesion.

    build_graph aprovecha graph_cache.pkl si existe, asi que tras la primera
    vez el arranque es casi instantaneo. El conteo de aristas y los limites del
    mapa se calculan aqui dentro a proposito: los dos recorren los 156.000
    nodos, y hacerlo en cada re-ejecucion solo para mostrar un numero seria un
    desperdicio.
    """
    graph, coordinates = build_graph(str(OSM_PATH))
    edge_count = sum(len(neighbors) for neighbors in graph.values())
    bounds = compute_map_bounds(coordinates)

    return RoadNetwork(graph, coordinates, edge_count, bounds)


def init_session_state():
    """Crea las claves de estado la primera vez que corre la aplicacion."""
    st.session_state.setdefault("origin", None)
    st.session_state.setdefault("goal", None)
    st.session_state.setdefault("last_click", None)
    st.session_state.setdefault("route", None)


def register_point(point):
    """Asigna el punto recibido al origen o al destino, en ese orden.

    Un tercer clic reinicia la seleccion y empieza un recorrido nuevo, que es
    lo que el usuario espera sin tener que pulsar ningun boton.
    """
    if st.session_state.origin is None:
        st.session_state.origin = point
    elif st.session_state.goal is None:
        st.session_state.goal = point
    else:
        st.session_state.origin = point
        st.session_state.goal = None

    # La ruta anterior ya no corresponde a los puntos elegidos.
    st.session_state.route = None


def set_points(origin, goal):
    """Fija origen y destino de una vez, desde los formularios de respaldo."""
    st.session_state.origin = origin
    st.session_state.goal = goal
    st.session_state.last_click = None
    st.session_state.route = None


def clear_points():
    """Borra la seleccion y la ruta calculada."""
    st.session_state.origin = None
    st.session_state.goal = None
    st.session_state.last_click = None
    st.session_state.route = None


def draw_route(road_map, coordinates):
    """Dibuja la ruta calculada sobre el mapa, si la hay y si tuvo exito."""
    route = st.session_state.route

    if route is None or not route["success"]:
        return

    polyline = route_polyline(route["path"], coordinates)
    if not polyline:
        return

    folium.PolyLine(
        polyline,
        color=ROUTE_COLOR,
        weight=6,
        opacity=0.85,
        tooltip="Ruta calculada",
    ).add_to(road_map)

    # Los extremos reales de la ruta no son donde el usuario hizo clic, sino
    # el nodo de la red vial mas cercano. Mostrarlos deja ver ese enganche.
    start_point, goal_point = route_endpoints(route["path"], coordinates)

    for point, label in ((start_point, "Nodo de partida"), (goal_point, "Nodo de llegada")):
        if point is not None:
            folium.CircleMarker(
                point,
                radius=6,
                color=ROUTE_COLOR,
                fill=True,
                fill_opacity=1.0,
                tooltip=label,
            ).add_to(road_map)

    road_map.fit_bounds(polyline)


def build_map(coordinates):
    """Arma el mapa de Folium con los marcadores y la ruta actual."""
    road_map = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    if st.session_state.origin is not None:
        folium.Marker(
            st.session_state.origin,
            tooltip="Origen",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(road_map)

    if st.session_state.goal is not None:
        folium.Marker(
            st.session_state.goal,
            tooltip="Destino",
            icon=folium.Icon(color="red", icon="flag"),
        ).add_to(road_map)

    draw_route(road_map, coordinates)

    return road_map


def handle_click(map_state):
    """Registra el ultimo punto clicado, ignorando las repeticiones.

    st_folium devuelve el MISMO last_clicked en cada re-ejecucion mientras el
    usuario no vuelva a pulsar sobre el mapa. Sin comparar contra el ultimo
    punto ya procesado, cualquier interaccion con otro control volveria a
    registrar el mismo clic y la seleccion avanzaria sola.
    """
    if not map_state:
        return

    clicked = map_state.get("last_clicked")
    if not clicked:
        return

    point = (round(clicked["lat"], 6), round(clicked["lng"], 6))

    if point == st.session_state.last_click:
        return

    st.session_state.last_click = point
    register_point(point)

    # Se vuelve a ejecutar para que el marcador aparezca de inmediato: el mapa
    # ya se dibujo mas arriba con el estado anterior.
    st.rerun()


def render_instructions(network):
    """Muestra las indicaciones paso a paso debajo del mapa.

    Es un requisito explicito del enunciado: no basta con dibujar la linea, hay
    que decir que hacer en cada cruce.
    """
    route = st.session_state.route

    if route is None or not route["success"]:
        return

    steps = generate_route_instructions(route, network.graph, network.coordinates)

    if not steps:
        return

    st.subheader("Pasos a seguir")

    # Una ruta larga puede pasar de veinte indicaciones; se dejan dentro de un
    # contenedor con desplazamiento para no empujar el mapa fuera de la vista.
    with st.container(height=260):
        st.markdown(
            "\n".join(f"{number}. {step}" for number, step in enumerate(steps, start=1))
        )


def render_selection():
    """Muestra que puntos estan elegidos y que se espera del usuario."""
    st.subheader("Puntos seleccionados")
    st.write(f"**Origen:** {format_point(st.session_state.origin)}")
    st.write(f"**Destino:** {format_point(st.session_state.goal)}")

    if st.session_state.origin is None:
        st.info("Haz clic en el mapa para elegir el punto de partida.")
    elif st.session_state.goal is None:
        st.info("Ahora haz clic en el punto de destino.")

    st.button("Reiniciar puntos", on_click=clear_points, use_container_width=True)


def render_search_controls(network):
    """Selector de criterio y de algoritmo, y el boton de calcular."""
    st.subheader("Búsqueda")

    mode_label = st.selectbox("Criterio", list(SEARCH_MODES))
    algorithm = st.selectbox("Algoritmo", AVAILABLE_ALGORITHMS)

    ready = st.session_state.origin is not None and st.session_state.goal is not None

    calculate = st.button(
        "Calcular ruta",
        type="primary",
        disabled=not ready,
        use_container_width=True,
    )

    if not calculate:
        return

    # El spinner no es adorno: la peticion que NO encuentra ruta es la mas
    # lenta del sistema, hasta 1,5 s recorriendo los 156.431 nodos. Sin
    # indicador el usuario cree que la aplicacion se colgo.
    with st.spinner("Calculando ruta…"):
        st.session_state.route = find_route(
            network.graph,
            network.coordinates,
            st.session_state.origin,
            st.session_state.goal,
            network.bounds,
            mode=SEARCH_MODES[mode_label],
            algorithm=algorithm,
        )

    # El mapa se dibujo antes de pulsar el boton: hay que repintarlo con la
    # ruta recien calculada.
    st.rerun()


def render_result():
    """Muestra el resultado de la ultima busqueda."""
    route = st.session_state.route

    if route is None:
        return

    st.subheader("Resultado")

    # Nunca se muestra una traza: el agente ya redacta el mensaje en español.
    if not route["success"]:
        st.warning(route["message"])
        return

    st.metric("Distancia", format_distance(route["distance_m"]))
    st.metric("Tiempo estimado", format_duration(route["estimated_time_s"]))

    st.caption(
        f"{format_count(len(route['path']))} nodos en la ruta · "
        f"{format_count(route['visited_nodes'])} nodos explorados · "
        f"{route['runtime_ms']:,.1f} ms · "
        f"{route['algorithm']} ({route['heuristic']})"
    )


def render_known_places():
    """Respaldo de la demostracion: rutas ya verificadas sobre el grafo."""
    names = list(KNOWN_PLACES)

    with st.form("lugares_conocidos"):
        origin_name = st.selectbox("Origen", names, index=0)
        goal_name = st.selectbox("Destino", names, index=1)
        submitted = st.form_submit_button(
            "Usar estos lugares",
            use_container_width=True,
        )

    if submitted:
        set_points(KNOWN_PLACES[origin_name], KNOWN_PLACES[goal_name])
        st.rerun()


def render_manual_coordinates():
    """Entrada manual de latitud y longitud, por si los clics fallan."""
    with st.form("coordenadas_manuales"):
        origin_lat = st.number_input("Latitud de origen", value=18.47177, format="%.5f")
        origin_lon = st.number_input("Longitud de origen", value=-69.88757, format="%.5f")
        goal_lat = st.number_input("Latitud de destino", value=18.47394, format="%.5f")
        goal_lon = st.number_input("Longitud de destino", value=-69.88385, format="%.5f")
        submitted = st.form_submit_button(
            "Usar estas coordenadas",
            use_container_width=True,
        )

    if submitted:
        set_points((origin_lat, origin_lon), (goal_lat, goal_lon))
        st.rerun()


def main():
    """Punto de entrada de la aplicacion."""
    st.set_page_config(
        page_title="Ruteo en Santo Domingo",
        page_icon="🗺️",
        layout="wide",
    )

    init_session_state()

    # Nunca se muestra una traza de error al usuario: si falta el mapa, se
    # explica que hacer y se detiene la aplicacion.
    if not OSM_PATH.exists():
        st.error(
            f"No se encuentra {OSM_PATH}. El archivo no viaja en el "
            "repositorio por su tamaño: cópialo en la carpeta data/ antes de "
            "abrir la aplicación."
        )
        st.stop()

    network = load_road_network()

    st.title("Ruteo en Santo Domingo")
    st.caption(
        f"Grafo dirigido con {len(network.graph):,} nodos y "
        f"{network.edge_count:,} aristas, construido desde datos de "
        "OpenStreetMap."
    )

    map_column, panel_column = st.columns([3, 1], gap="medium")

    with map_column:
        map_state = st_folium(
            build_map(network.coordinates),
            height=MAP_HEIGHT,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key="mapa",
        )

    # Se procesa antes de dibujar el resto para que no muestre datos viejos.
    handle_click(map_state)

    with map_column:
        render_instructions(network)

    with panel_column:
        render_selection()
        render_search_controls(network)
        render_result()

        with st.expander("Lugares verificados"):
            render_known_places()

        with st.expander("Coordenadas manuales"):
            render_manual_coordinates()


if __name__ == "__main__":
    main()
