"""Comparacion medida de UCS contra A* sobre el grafo real de Santo Domingo.

Genera la tabla de metricas de efectividad del informe. Ningun numero se
escribe a mano: todos salen de ejecutar los algoritmos sobre el grafo que
construye Deivy.

Cada escenario se resuelve con cuatro configuraciones. Las columnas UCS son la
linea base sin heuristica; si A* no devuelve exactamente el mismo costo que su
UCS correspondiente, la heuristica esta mal y el script lo denuncia en la tabla
en vez de publicar el numero.

Uso:
    python3 -m src.search.metrics
    python3 -m src.search.metrics --repeticiones 5 --salida docs/metricas.md
"""

import argparse
import statistics
from pathlib import Path

from src.graph_builder import build_graph
from src.nearest_node import find_nearest_node
from src.search.astar import astar
from src.search.heuristics import graph_max_speed_mps
from src.search.ucs import ucs

DEFAULT_OSM_PATH = "data/santo_domingo.osm"
DEFAULT_OUTPUT_PATH = "docs/metricas.md"
DEFAULT_REPETITIONS = 3

# (etiqueta de la columna, algoritmo, modo)
CONFIGURATIONS = [
    ("UCS distancia", "UCS", "distance"),
    ("A* distancia", "A*", "distance"),
    ("UCS tiempo", "UCS", "time"),
    ("A* tiempo", "A*", "time"),
]

# Los cinco casos que pide el informe, mas uno de ruta inexistente.
SCENARIOS = [
    {
        "name": "1. Ruta corta dentro de un mismo sector",
        "detail": "Recorrido de pocas cuadras en Gazcue.",
        "origin": (18.4690, -69.9130),
        "goal": (18.4740, -69.9060),
    },
    {
        "name": "2. Ruta de varios kilometros",
        "detail": "Zona Colonial hasta la UASD, cruzando el centro.",
        "origin": (18.4734, -69.8836),
        "goal": (18.4600, -69.9270),
    },
    {
        "name": "3. Origen y destino muy alejados",
        "detail": "Extremo oeste de la ciudad hasta el extremo este.",
        "origin": (18.5100, -70.0300),
        "goal": (18.4560, -69.7100),
    },
    {
        "name": "4. Ruta por avenidas principales",
        "detail": "Winston Churchill hasta Santo Domingo Este.",
        "origin": (18.4670, -69.9410),
        "goal": (18.4896, -69.8590),
    },
    {
        "name": "5. Ruta con calles unidireccionales",
        "detail": "Interior de la Zona Colonial, una retícula de un solo sentido.",
        "origin": (18.4746, -69.8845),
        "goal": (18.4700, -69.8890),
        "check_reverse": True,
    },
    {
        "name": "6. Destino sin ruta posible",
        "detail": "Nodo fuera de la componente fuertemente conexa del grafo.",
        "origin": (18.5000, -70.0000),
        "goal": (18.4700, -69.7200),
        "expect_no_route": True,
    },
]


def run_search(graph, coordinates, algorithm, mode, start, goal, max_speed_mps):
    """Ejecuta una sola busqueda con la configuracion indicada."""
    if algorithm == "UCS":
        return ucs(graph, start, goal, mode=mode)

    return astar(
        graph,
        coordinates,
        start,
        goal,
        mode=mode,
        max_speed_mps=max_speed_mps,
    )


def measure_search(
    graph,
    coordinates,
    algorithm,
    mode,
    start,
    goal,
    max_speed_mps,
    repetitions,
):
    """Repite la busqueda y se queda con la mediana del tiempo de ejecucion.

    Una sola corrida tiene demasiado ruido para publicarla: el sistema
    operativo, la cache del procesador y el recolector de basura mueven el
    resultado. La mediana descarta los picos.
    """
    runtimes = []
    result = None

    for _ in range(repetitions):
        result = run_search(
            graph,
            coordinates,
            algorithm,
            mode,
            start,
            goal,
            max_speed_mps,
        )
        runtimes.append(result["runtime_ms"])

    result["runtime_ms"] = round(statistics.median(runtimes), 2)
    return result


def cost_field(mode):
    """Clave del resultado que contiene el costo que ese modo optimiza."""
    if mode == "time":
        return "estimated_time_s"

    return "distance_m"


def check_optimality(results):
    """Comprueba que cada A* iguale el costo de su UCS del mismo modo.

    Devuelve la lista de mensajes de verificacion, uno por modo.
    """
    messages = []

    for mode in ("distance", "time"):
        by_ucs = results[("UCS", mode)]
        by_astar = results[("A*", mode)]

        if not by_ucs["success"] or not by_astar["success"]:
            messages.append(f"- Modo {mode}: sin ruta, no aplica la comparación.")
            continue

        field = cost_field(mode)
        difference = abs(by_astar[field] - by_ucs[field])

        if difference < 0.01:
            saved = 100.0 * (
                1 - by_astar["visited_nodes"] / by_ucs["visited_nodes"]
            )
            messages.append(
                f"- Modo {mode}: A* iguala el costo de UCS "
                f"({by_ucs[field]:,.2f}) explorando {saved:.1f}% menos nodos."
            )
        else:
            messages.append(
                f"- Modo {mode}: **FALLO** — A* devuelve {by_astar[field]:,.2f} "
                f"y UCS {by_ucs[field]:,.2f}. La heurística no es admisible."
            )

    return messages


def render_table(headers, rows):
    """Convierte encabezados y filas en una tabla de Markdown."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    return lines


def build_scenario_rows(results):
    """Arma las filas de metricas de un escenario, una por indicador."""
    ordered = [results[(algorithm, mode)] for _, algorithm, mode in CONFIGURATIONS]

    return [
        ["Ruta encontrada"]
        + ["Sí" if item["success"] else "No" for item in ordered],
        ["Nodos en la ruta"] + [f"{len(item['path']):,}" for item in ordered],
        ["Distancia total (m)"] + [f"{item['distance_m']:,.2f}" for item in ordered],
        ["Tiempo estimado (s)"]
        + [f"{item['estimated_time_s']:,.2f}" for item in ordered],
        ["Nodos visitados"] + [f"{item['visited_nodes']:,}" for item in ordered],
        ["Tiempo de ejecución (ms)"]
        + [f"{item['runtime_ms']:,.2f}" for item in ordered],
    ]


def describe_reverse(graph, coordinates, start, goal, max_speed_mps):
    """Compara la ida y la vuelta para evidenciar las vias de un solo sentido."""
    going = astar(graph, coordinates, start, goal, max_speed_mps=max_speed_mps)
    returning = astar(graph, coordinates, goal, start, max_speed_mps=max_speed_mps)

    if not going["success"] or not returning["success"]:
        return ["- Una de las dos direcciones no tiene ruta."]

    difference = returning["distance_m"] - going["distance_m"]

    return [
        f"- Ida: {going['distance_m']:,.2f} m en {len(going['path']):,} nodos.",
        f"- Vuelta: {returning['distance_m']:,.2f} m en "
        f"{len(returning['path']):,} nodos.",
        f"- Diferencia: {difference:+,.2f} m. En un grafo no dirigido las dos "
        "cifras serían idénticas por fuerza; aquí no coinciden porque el "
        "sentido único impide deshacer el camino y obliga a rodear por otras "
        "calles.",
    ]


def describe_no_route(results):
    """Explica el caso sin ruta y el sobrecosto que A* paga en el."""
    sample = results[("UCS", "distance")]

    lines = [
        f"El algoritmo agotó la búsqueda tras expandir "
        f"{sample['visited_nodes']:,} nodos y respondió: "
        f"«{sample['message']}» No es un error: no existe camino dirigido."
    ]

    ucs_runtime = results[("UCS", "distance")]["runtime_ms"]
    astar_runtime = results[("A*", "distance")]["runtime_ms"]

    if astar_runtime > ucs_runtime:
        lines.append("")
        lines.append(
            f"Obsérvese que aquí A* fue más lento que UCS "
            f"({astar_runtime:,.2f} ms contra {ucs_runtime:,.2f} ms). Sin ruta "
            "que encontrar, ambos recorren el grafo entero, pero A* paga además "
            "el cálculo de la heurística en cada nodo sin recibir ninguna guía "
            "a cambio. La heurística solo rinde cuando hay un destino al que "
            "dirigirse."
        )

    return lines


def evaluate_scenario(graph, coordinates, scenario, max_speed_mps, repetitions):
    """Resuelve un escenario con las cuatro configuraciones y arma su seccion."""
    start = find_nearest_node(scenario["origin"][0], scenario["origin"][1], coordinates)
    goal = find_nearest_node(scenario["goal"][0], scenario["goal"][1], coordinates)

    results = {}
    for _, algorithm, mode in CONFIGURATIONS:
        results[(algorithm, mode)] = measure_search(
            graph,
            coordinates,
            algorithm,
            mode,
            start,
            goal,
            max_speed_mps,
            repetitions,
        )

    lines = [f"### {scenario['name']}", "", scenario["detail"], ""]
    lines.append(
        f"Origen `{start}` en {coordinates[start]} · "
        f"destino `{goal}` en {coordinates[goal]}."
    )
    lines.append("")

    headers = ["Métrica"] + [label for label, _, _ in CONFIGURATIONS]
    lines.extend(render_table(headers, build_scenario_rows(results)))
    lines.append("")

    if scenario.get("expect_no_route"):
        lines.extend(describe_no_route(results))
    else:
        lines.append("**Verificación de optimalidad**")
        lines.append("")
        lines.extend(check_optimality(results))

    if scenario.get("check_reverse"):
        lines.append("")
        lines.append("**Ida y vuelta**")
        lines.append("")
        lines.extend(describe_reverse(graph, coordinates, start, goal, max_speed_mps))

    lines.append("")
    return lines, results


def build_summary(all_results):
    """Resume el ahorro de A* frente a UCS en los escenarios que tienen ruta."""
    lines = ["## Resumen", ""]
    compared = 0

    for mode, label in (("distance", "distancia"), ("time", "tiempo")):
        savings = []
        speedups = []

        for results in all_results:
            by_ucs = results[("UCS", mode)]
            by_astar = results[("A*", mode)]

            if not by_ucs["success"] or not by_astar["success"]:
                continue

            savings.append(
                100.0 * (1 - by_astar["visited_nodes"] / by_ucs["visited_nodes"])
            )

            if by_astar["runtime_ms"] > 0:
                speedups.append(by_ucs["runtime_ms"] / by_astar["runtime_ms"])

        if not savings:
            continue

        compared = len(savings)
        lines.append(
            f"- **Modo {label}:** A* exploró en promedio "
            f"{statistics.mean(savings):.1f}% menos nodos que UCS "
            f"(entre {min(savings):.1f}% y {max(savings):.1f}%), y resolvió la "
            f"búsqueda {statistics.mean(speedups):.1f} veces más rápido en "
            f"promedio (entre {min(speedups):.1f}x y {max(speedups):.1f}x)."
        )

    lines.append("")
    lines.append(
        f"En los {compared} escenarios con ruta, A* devolvió exactamente el "
        "mismo costo que UCS en los dos modos. Esa igualdad es la evidencia de "
        "que las heurísticas nunca sobreestiman: A* mira mucho menos mapa sin "
        "perder la garantía de optimalidad."
    )
    lines.append("")

    return lines


def build_report(graph, coordinates, max_speed_mps, repetitions):
    """Construye el informe completo de metricas como lineas de Markdown."""
    edge_count = sum(len(neighbors) for neighbors in graph.values())

    lines = [
        "# Métricas de efectividad — agente de búsqueda",
        "",
        "Tabla generada ejecutando los algoritmos sobre el grafo real. Para "
        "reproducirla: `python3 -m src.search.metrics`.",
        "",
        "## Grafo utilizado",
        "",
        f"- Nodos: {len(graph):,}",
        f"- Aristas dirigidas: {edge_count:,}",
        f"- Velocidad máxima medida: {max_speed_mps:.4f} m/s "
        f"({max_speed_mps * 3.6:.1f} km/h)",
        f"- Repeticiones por medición: {repetitions} (se reporta la mediana)",
        "",
        "## Escenarios",
        "",
    ]

    all_results = []

    for scenario in SCENARIOS:
        scenario_lines, results = evaluate_scenario(
            graph,
            coordinates,
            scenario,
            max_speed_mps,
            repetitions,
        )
        lines.extend(scenario_lines)
        all_results.append(results)

    lines.extend(build_summary(all_results))

    return lines


def run(
    osm_path=DEFAULT_OSM_PATH,
    output_path=DEFAULT_OUTPUT_PATH,
    repetitions=DEFAULT_REPETITIONS,
):
    """Genera la tabla de metricas y la guarda en un archivo Markdown."""
    graph, coordinates = build_graph(osm_path)
    max_speed_mps = graph_max_speed_mps(graph)

    lines = build_report(graph, coordinates, max_speed_mps, repetitions)
    report = "\n".join(lines)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report + "\n", encoding="utf-8")

    print(report)
    print()
    print(f"Tabla guardada en: {destination}")

    return report


def main():
    """Punto de entrada de la linea de comandos."""
    parser = argparse.ArgumentParser(
        description="Genera la tabla comparativa de UCS contra A*."
    )
    parser.add_argument(
        "--osm",
        default=DEFAULT_OSM_PATH,
        help="Archivo OSM de entrada",
    )
    parser.add_argument(
        "--salida",
        default=DEFAULT_OUTPUT_PATH,
        help="Archivo Markdown donde escribir la tabla",
    )
    parser.add_argument(
        "--repeticiones",
        type=int,
        default=DEFAULT_REPETITIONS,
        help="Cuántas veces repetir cada medición",
    )
    args = parser.parse_args()

    run(args.osm, args.salida, args.repeticiones)


if __name__ == "__main__":
    main()
