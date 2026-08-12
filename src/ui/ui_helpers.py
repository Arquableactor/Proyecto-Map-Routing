"""Formateo de numeros y coordenadas para mostrarlos al usuario.

Ninguna de estas funciones depende de Streamlit ni de Folium: son
transformaciones de datos a texto, y por eso se pueden probar sueltas. Viven en
un solo sitio para que la aplicacion y las instrucciones paso a paso no acaben
con dos maneras distintas de escribir la misma distancia.
"""

METERS_PER_KILOMETER = 1000.0
SECONDS_PER_MINUTE = 60.0
MINUTES_PER_HOUR = 60.0


def format_distance(meters):
    """Convierte metros en un texto legible.

    Por debajo de un kilometro se dan metros redondeados, porque el decimal no
    aporta nada al conducir. Por encima se pasa a kilometros con un decimal:
    "1.2 kilómetros" se lee mucho mejor que "1234 metros".
    """
    if meters < METERS_PER_KILOMETER:
        rounded = round(meters)

        if rounded == 1:
            return "1 metro"

        return f"{rounded:,.0f} metros".replace(",", " ")

    return f"{meters / METERS_PER_KILOMETER:.1f} kilómetros"


def format_duration(seconds):
    """Convierte segundos en un texto legible.

    El agente devuelve segundos crudos porque es lo que necesita para comparar
    rutas, pero "243 segundos" no le dice nada a una persona: son 4 minutos.
    """
    if seconds < SECONDS_PER_MINUTE:
        rounded = round(seconds)

        if rounded == 1:
            return "1 segundo"

        return f"{rounded:.0f} segundos"

    minutes = seconds / SECONDS_PER_MINUTE

    if minutes < MINUTES_PER_HOUR:
        rounded = round(minutes)

        if rounded == 1:
            return "1 minuto"

        return f"{rounded:.0f} minutos"

    hours = int(minutes // MINUTES_PER_HOUR)
    remaining_minutes = int(round(minutes % MINUTES_PER_HOUR))

    if remaining_minutes == 0:
        return f"{hours} h"

    return f"{hours} h {remaining_minutes} min"


def format_point(point):
    """Formatea un par (latitud, longitud) para mostrarlo en pantalla."""
    if point is None:
        return "sin elegir"

    return f"{point[0]:.5f}, {point[1]:.5f}"


def format_count(value):
    """Separa los miles con espacio fino, como se escribe en español."""
    return f"{value:,}".replace(",", " ")
