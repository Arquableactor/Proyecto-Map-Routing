# Métricas de efectividad — agente de búsqueda

Tabla generada ejecutando los algoritmos sobre el grafo real. Para reproducirla: `python3 -m src.search.metrics`.

## Grafo utilizado

- Nodos: 156,431
- Aristas dirigidas: 328,071
- Velocidad máxima medida: 27.7778 m/s (100.0 km/h)
- Repeticiones por medición: 5 (se reporta la mediana)

## Escenarios

### 1. Ruta corta dentro de un mismo sector

Recorrido de pocas cuadras en Gazcue.

Origen `6427818349` en (18.4688022, -69.9134302) · destino `308898674` en (18.4742863, -69.9057079).

| Métrica | UCS distancia | A* distancia | UCS tiempo | A* tiempo |
|---|---|---|---|---|
| Ruta encontrada | Sí | Sí | Sí | Sí |
| Nodos en la ruta | 40 | 40 | 25 | 25 |
| Distancia total (m) | 1,316.44 | 1,316.44 | 1,327.64 | 1,327.64 |
| Tiempo estimado (s) | 136.71 | 136.71 | 95.90 | 95.90 |
| Nodos visitados | 667 | 140 | 608 | 293 |
| Tiempo de ejecución (ms) | 2.21 | 0.82 | 1.20 | 1.43 |

**Verificación de optimalidad**

- Modo distance: A* iguala el costo de UCS (1,316.44) explorando 79.0% menos nodos.
- Modo time: A* iguala el costo de UCS (95.90) explorando 51.8% menos nodos.

### 2. Ruta de varios kilometros

Zona Colonial hasta la UASD, cruzando el centro.

Origen `4090286869` en (18.4733151, -69.8834941) · destino `3306094452` en (18.4597983, -69.9270944).

| Métrica | UCS distancia | A* distancia | UCS tiempo | A* tiempo |
|---|---|---|---|---|
| Ruta encontrada | Sí | Sí | Sí | Sí |
| Nodos en la ruta | 100 | 100 | 193 | 193 |
| Distancia total (m) | 5,364.11 | 5,364.11 | 6,707.85 | 6,707.85 |
| Tiempo estimado (s) | 470.45 | 470.45 | 427.47 | 427.47 |
| Nodos visitados | 14,603 | 407 | 15,259 | 4,851 |
| Tiempo de ejecución (ms) | 33.82 | 2.29 | 38.31 | 25.37 |

**Verificación de optimalidad**

- Modo distance: A* iguala el costo de UCS (5,364.11) explorando 97.2% menos nodos.
- Modo time: A* iguala el costo de UCS (427.47) explorando 68.2% menos nodos.

### 3. Origen y destino muy alejados

Extremo oeste de la ciudad hasta el extremo este.

Origen `1865979314` en (18.5101922, -70.0299763) · destino `6770513642` en (18.4554708, -69.7098559).

| Métrica | UCS distancia | A* distancia | UCS tiempo | A* tiempo |
|---|---|---|---|---|
| Ruta encontrada | Sí | Sí | Sí | Sí |
| Nodos en la ruta | 641 | 641 | 658 | 658 |
| Distancia total (m) | 37,242.03 | 37,242.03 | 37,877.35 | 37,877.35 |
| Tiempo estimado (s) | 1,820.12 | 1,820.12 | 1,775.61 | 1,775.61 |
| Nodos visitados | 155,845 | 41,974 | 151,408 | 49,838 |
| Tiempo de ejecución (ms) | 438.36 | 269.69 | 496.73 | 343.44 |

**Verificación de optimalidad**

- Modo distance: A* iguala el costo de UCS (37,242.03) explorando 73.1% menos nodos.
- Modo time: A* iguala el costo de UCS (1,775.61) explorando 67.1% menos nodos.

### 4. Ruta por avenidas principales

Winston Churchill hasta Santo Domingo Este.

Origen `309719985` en (18.4669623, -69.9411318) · destino `309913835` en (18.4894509, -69.8593997).

| Métrica | UCS distancia | A* distancia | UCS tiempo | A* tiempo |
|---|---|---|---|---|
| Ruta encontrada | Sí | Sí | Sí | Sí |
| Nodos en la ruta | 179 | 179 | 156 | 156 |
| Distancia total (m) | 10,175.05 | 10,175.05 | 10,378.14 | 10,378.14 |
| Tiempo estimado (s) | 792.23 | 792.23 | 626.89 | 626.89 |
| Nodos visitados | 59,057 | 5,443 | 55,341 | 15,416 |
| Tiempo de ejecución (ms) | 147.84 | 29.62 | 140.49 | 87.07 |

**Verificación de optimalidad**

- Modo distance: A* iguala el costo de UCS (10,175.05) explorando 90.8% menos nodos.
- Modo time: A* iguala el costo de UCS (626.89) explorando 72.1% menos nodos.

### 5. Ruta con calles unidireccionales

Interior de la Zona Colonial, una retícula de un solo sentido.

Origen `308757848` en (18.4746759, -69.8846833) · destino `308695338` en (18.470146, -69.8889062).

| Métrica | UCS distancia | A* distancia | UCS tiempo | A* tiempo |
|---|---|---|---|---|
| Ruta encontrada | Sí | Sí | Sí | Sí |
| Nodos en la ruta | 14 | 14 | 22 | 22 |
| Distancia total (m) | 1,104.25 | 1,104.25 | 1,299.44 | 1,299.44 |
| Tiempo estimado (s) | 118.99 | 118.99 | 109.74 | 109.74 |
| Nodos visitados | 349 | 42 | 321 | 158 |
| Tiempo de ejecución (ms) | 0.50 | 0.26 | 0.69 | 0.75 |

**Verificación de optimalidad**

- Modo distance: A* iguala el costo de UCS (1,104.25) explorando 88.0% menos nodos.
- Modo time: A* iguala el costo de UCS (109.74) explorando 50.8% menos nodos.

**Ida y vuelta**

- Ida: 1,104.25 m en 14 nodos.
- Vuelta: 867.28 m en 14 nodos.
- Diferencia: -236.97 m. En un grafo no dirigido las dos cifras serían idénticas por fuerza; aquí no coinciden porque el sentido único impide deshacer el camino y obliga a rodear por otras calles.

### 6. Destino sin ruta posible

Nodo fuera de la componente fuertemente conexa del grafo.

Origen `6381244708` en (18.5001651, -70.0001679) · destino `1867212404` en (18.4591714, -69.7235902).

| Métrica | UCS distancia | A* distancia | UCS tiempo | A* tiempo |
|---|---|---|---|---|
| Ruta encontrada | No | No | No | No |
| Nodos en la ruta | 0 | 0 | 0 | 0 |
| Distancia total (m) | 0.00 | 0.00 | 0.00 | 0.00 |
| Tiempo estimado (s) | 0.00 | 0.00 | 0.00 | 0.00 |
| Nodos visitados | 155,875 | 155,875 | 155,875 | 155,875 |
| Tiempo de ejecución (ms) | 434.99 | 1,056.90 | 497.63 | 1,059.25 |

El algoritmo agotó la búsqueda tras expandir 155,875 nodos y respondió: «No se encontró una ruta entre los puntos seleccionados.» No es un error: no existe camino dirigido.

Obsérvese que aquí A* fue más lento que UCS (1,056.90 ms contra 434.99 ms). Sin ruta que encontrar, ambos recorren el grafo entero, pero A* paga además el cálculo de la heurística en cada nodo sin recibir ninguna guía a cambio. La heurística solo rinde cuando hay un destino al que dirigirse.

## Resumen

- **Modo distancia:** A* exploró en promedio 85.6% menos nodos que UCS (entre 73.1% y 97.2%), y resolvió la búsqueda 5.2 veces más rápido en promedio (entre 1.6x y 14.8x).
- **Modo tiempo:** A* exploró en promedio 62.0% menos nodos que UCS (entre 50.8% y 72.1%), y resolvió la búsqueda 1.3 veces más rápido en promedio (entre 0.8x y 1.6x).

En los 5 escenarios con ruta, A* devolvió exactamente el mismo costo que UCS en los dos modos. Esa igualdad es la evidencia de que las heurísticas nunca sobreestiman: A* mira mucho menos mapa sin perder la garantía de optimalidad.

