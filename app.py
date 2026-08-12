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

Ejecutar con:
    streamlit run app.py
"""

from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

from src.graph_builder import build_graph

OSM_PATH = Path("data/santo_domingo.osm")

# Centro y zoom elegidos a partir de la caja real del grafo,
# lat 18.390-18.653 y lon -70.169 a -69.693.
MAP_CENTER = (18.48, -69.93)
MAP_ZOOM = 12
MAP_HEIGHT = 560

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


@st.cache_resource(show_spinner="Construyendo el grafo vial de Santo Domingo…")
def load_road_graph():
    """Carga el grafo una sola vez y lo reutiliza en toda la sesion.

    build_graph aprovecha graph_cache.pkl si existe, asi que tras la primera
    vez el arranque es casi instantaneo. El conteo de aristas se calcula aqui
    dentro a proposito: recorrer 156.000 nodos en cada re-ejecucion solo para
    mostrar un numero seria un desperdicio.
    """
    graph, coordinates = build_graph(str(OSM_PATH))
    edge_count = sum(len(neighbors) for neighbors in graph.values())
    return graph, coordinates, edge_count


def init_session_state():
    """Crea las claves de estado la primera vez que corre la aplicacion."""
    st.session_state.setdefault("origin", None)
    st.session_state.setdefault("goal", None)
    st.session_state.setdefault("last_click", None)


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


def clear_points():
    """Borra la seleccion completa."""
    st.session_state.origin = None
    st.session_state.goal = None
    st.session_state.last_click = None


def build_map():
    """Arma el mapa de Folium con los marcadores que ya estan elegidos."""
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


def format_point(point):
    """Formatea un par de coordenadas para mostrarlo en pantalla."""
    if point is None:
        return "sin elegir"

    return f"{point[0]:.5f}, {point[1]:.5f}"


def render_selection():
    """Muestra que puntos estan elegidos y que se espera del usuario."""
    st.subheader("Puntos seleccionados")
    st.write(f"**Origen:** {format_point(st.session_state.origin)}")
    st.write(f"**Destino:** {format_point(st.session_state.goal)}")

    if st.session_state.origin is None:
        st.info("Haz clic en el mapa para elegir el punto de partida.")
    elif st.session_state.goal is None:
        st.info("Ahora haz clic en el punto de destino.")
    else:
        st.success("Origen y destino listos.")

    st.button("Reiniciar puntos", on_click=clear_points, use_container_width=True)


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
        st.session_state.origin = KNOWN_PLACES[origin_name]
        st.session_state.goal = KNOWN_PLACES[goal_name]
        st.session_state.last_click = None
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
        st.session_state.origin = (origin_lat, origin_lon)
        st.session_state.goal = (goal_lat, goal_lon)
        st.session_state.last_click = None
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

    graph, coordinates, edge_count = load_road_graph()

    st.title("Ruteo en Santo Domingo")
    st.caption(
        f"Grafo dirigido con {len(graph):,} nodos y {edge_count:,} aristas, "
        "construido desde datos de OpenStreetMap."
    )

    map_column, panel_column = st.columns([3, 1], gap="medium")

    with map_column:
        map_state = st_folium(
            build_map(),
            height=MAP_HEIGHT,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key="mapa",
        )

    # Se procesa antes de dibujar el panel para que no muestre datos viejos.
    handle_click(map_state)

    with panel_column:
        render_selection()

        with st.expander("Lugares verificados"):
            render_known_places()

        with st.expander("Coordenadas manuales"):
            render_manual_coordinates()


if __name__ == "__main__":
    main()
